# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-04-26 

__updated__ = "2020-08-13"
__version__ = "1.7"

from pysmartnode import config
import uasyncio as asyncio
from pysmartnode.utils import sys_vars
from .definitions import *
import gc
from pysmartnode import logging

# This module is used to create components.
# This could be sensors, switches, binary_sensors etc.
# It provides a base class for linking components and subscribed topics and
# provides the basis for homeassistant autodiscovery.
# Helping components like arduino, i2c and similar that only provide helper objects (like Pins)
# don't need to use this module as a basis.

_mqtt = config.getMQTT()

# prevent multiple discoveries from running concurrently and creating Out-Of-Memory errors
# or queue overflow errors. This is a starting pointer using _next_component to progress.
_init_queue_start = None

_components = None  # pointer list of all registered components, used for mqtt etc


class ComponentBase:
    """
    Use this class as a base for components. Subclass to extend. See the template for examples.
    """

    def __init__(self, component_name, version, unit_index: int, discover=True, logger=None):
        """
        Base component class
        :param component_name: name of the component that is subclassing this switch (used for discovery and topics)
        :param version: version of the component module. will be logged over mqtt
        :param unit_index: counter of the registerd unit of this sensor_type (used for default topics)
        :param discover: if the component should send a discovery message, used in Home-Assistant.
        :param logger: optional logger instance. If not provided, one will be created with the component name
        """
        self._next_component = None  # needed to keep a list of registered components
        global _components
        if _components is None:
            _components = self
        else:
            c = _components
            while c is not None:
                if c._next_component is None:
                    c._next_component = self
                    break
                c = c._next_component
        # Workaround to prevent every component object from creating a new asyncio task for
        # network oriented initialization as this would cause a big RAM demand.
        global _init_queue_start
        if _init_queue_start is None:
            _init_queue_start = self
            asyncio.create_task(self.__initNetworkProcess())
        self.COMPONENT_NAME = component_name
        self.VERSION = version
        self._count = unit_index
        self.__discover = discover
        self._log = logger or logging.getLogger("{!s}{!s}".format(component_name, self._count))

    @staticmethod
    async def removeComponent(component):
        if type(component) == str:
            component = config.getComponent(component)
        if not isinstance(component, ComponentBase):
            config._log.error(
                "Can't remove a component that is not an instance of pysmartnode.utils.component.Component")
            return False
        # call cleanup method, should stop running loops
        await component._remove()
        global _components
        c = _components
        p = None
        while c is not None:
            if c == component:
                if p is None:
                    _components = c._next_component
                    break
                p._next_component = c._next_component
                break
            p = c
            c = c._next_component

    async def _remove(self):
        """
        Cleanup method.
        Stop all loops and unsubscribe all topics.
        Also removes the component from Home-Assistant if discovery is enabled.
        """
        await _mqtt.unsubscribe(None, self)
        await config._log.asyncLog("info", "Removed component", config.getComponentName(self),
                                   "module", self.COMPONENT_NAME, "version", self.VERSION,
                                   timeout=5)
        if config.MQTT_DISCOVERY_ENABLED and self.__discover:
            await self._discovery(False)

    @staticmethod
    async def __initNetworkProcess():
        global _init_queue_start
        c = _init_queue_start
        while c is not None:
            await c._init_network()
            gc.collect()
            c = c._next_component
        _init_queue_start = None

    async def _init_network(self):
        await config._log.asyncLog("info", "Added module", self.COMPONENT_NAME, "version",
                                   self.VERSION, "as component", config.getComponentName(self),
                                   timeout=5)
        gc.collect()
        if config.MQTT_DISCOVERY_ENABLED and self.__discover:
            await self._discovery(True)
            gc.collect()

    async def _discovery(self, register=True):
        """
        Implement in subclass.
        Is only called by self._init_network if config.MQTT_DISCOVERY_ON_RECONNECT is True
        and by self._remove() when a componen is removed during runtime (e.g. sensor change).
        If register is False, send discovery message with empty message "" to remove the component
        from Homeassistant.
        """
        pass

    @staticmethod
    async def _publishDiscovery(component_type, component_topic, unique_name, discovery_type,
                                friendly_name=None):
        topic = ComponentBase._getDiscoveryTopic(component_type, unique_name)
        msg = ComponentBase._composeDiscoveryMsg(component_topic, unique_name, discovery_type,
                                                 friendly_name)
        await _mqtt.publish(topic, msg, qos=1, retain=True)
        del msg, topic
        gc.collect()

    @staticmethod
    async def _deleteDiscovery(component_type, unique_name):
        topic = ComponentBase._getDiscoveryTopic(component_type, unique_name)
        await _mqtt.publish(topic, "", qos=1, retain=True)

    @staticmethod
    def _composeAvailability():
        return DISCOVERY_AVAILABILITY.format(config.MQTT_HOME, sys_vars.getDeviceID(),
                                             config.MQTT_AVAILABILITY_SUBTOPIC)

    @staticmethod
    def _composeDiscoveryMsg(component_topic, name, component_type_discovery, friendly_name=None,
                             no_avail=False):
        """
        Helper function to separate dynamic system values from user defineable values.
        :param component_topic: state topic of the component. device topics (see mqtt) are supported
        :param name: name of the component, must be unique on the device, typically composed of component name and count
        :param component_type_discovery: discovery values for the component type, e.g. switch, sensor
        :param friendly_name: optional a readable name that is used in the gui and entity_id
        :param no_avail: don't add availability configs (typically only used for the availability component itself)
        :return: str
        """
        friendly_name = friendly_name or name
        component_topic = component_topic if _mqtt.isDeviceTopic(
            component_topic) is False else _mqtt.getRealTopic(
            component_topic)
        return DISCOVERY_BASE.format(component_topic,  # "~" component state topic
                                     friendly_name,  # name
                                     sys_vars.getDeviceID(), name,  # unique_id
                                     "" if no_avail else ComponentBase._composeAvailability(),
                                     component_type_discovery,  # component type specific values
                                     sys_vars.getDeviceDiscovery())  # device

    @staticmethod
    def _composeSensorType(device_class, unit_of_measurement="", value_template=VALUE_TEMPLATE,
                           expire_after=0, binary=False):
        """Just to make it easier for component developers."""
        if not binary:
            return DISCOVERY_SENSOR.format(device_class, unit_of_measurement, value_template,
                                           int(expire_after))
        return DISCOVERY_BINARY_SENSOR.format(device_class, int(expire_after))

    @staticmethod
    def _getDiscoveryTopic(component_type, name):
        return "{!s}/{!s}/{!s}/{!s}/config".format(config.MQTT_DISCOVERY_PREFIX, component_type,
                                                   sys_vars.getDeviceID(), name)

    @staticmethod
    def checkSensorType(obj, sensor_type):
        from .sensor import ComponentSensor
        if not isinstance(obj, ComponentSensor):
            raise TypeError("{!s} is not of instance ComponentSensor".format(obj))
        if sensor_type not in obj.sensor_types:
            raise TypeError("{!s} does not support the sensor_type {!s}".format(obj, sensor_type))

    @staticmethod
    def checkSwitchType(obj):
        from .switch import ComponentSwitch
        if not isinstance(obj, ComponentSwitch):
            raise TypeError("{!s} is not of instance ComponentSwitch".format(obj))
