# Author: Kevin Köck
# Copyright Kevin Köck 2019-2020 Released under the MIT license
# Created on 2019-09-10

"""
example config for remoteConfig module or as json in components.py:
{
    package: <package_path>
    component: Button
    constructor_args: {}
}
NOTE: additional constructor arguments are available from base classes, check COMPONENTS.md!
"""

# A button is basically a switch with a single-shot action that deactivates itself afterwards.

__updated__ = "2020-04-03"
__version__ = "0.81"

from pysmartnode import config
from pysmartnode.utils.component.button import ComponentButton

####################
# choose a component name that will be used for logging (not in leightweight_log),
# the default mqtt topic that can be changed by received or local component configuration
# as well as for the component name in homeassistant.
COMPONENT_NAME = "Button"
####################

_mqtt = config.getMQTT()
_unit_index = -1


class Button(ComponentButton):
    def __init__(self, **kwargs):
        # This makes it possible to use multiple instances of Button.
        # It is needed for every default value for mqtt.
        # Initialize before super()__init__(...) to not pass the wrong value.
        global _unit_index
        _unit_index += 1

        # set the initial state otherwise it will be "None" (unknown) and the first request
        # will set it accordingly which in case of a button will always be an activation.
        initial_state = False  # A button will always be False as it is single-shot,
        # unless you have a device with a long single-shot action active during reboot.
        # You might be able to poll the current state of a device to set the inital state correctly

        super().__init__(COMPONENT_NAME, __version__, _unit_index,
                         wait_for_lock=False, initial_state=initial_state, **kwargs)

        # If the device needs extra code, launch a new coroutine.

    #####################
    # Change this method according to your device.
    #####################
    async def _on(self) -> bool:
        """Turn device on."""
        pass
        # no return needed because of single-shot action.
        # If turning device on fails, it should be handled inside this method

    #####################
