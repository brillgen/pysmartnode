#!/usr/bin/env bash
rsync -av --delete pysmartnode_4M /home/kevin/micropython/ports/esp8266/boards/
cd ~/micropython/ports/esp8266/modules
rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/pysmartnode/" ./pysmartnode/ --delete
#rsync -av --prune-empty-dirs --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/_testing/" ./_testing/ --delete
rsync -av --prune-empty-dirs  --include "*/" --include "*.py" --exclude "*" --exclude "*.*" "/home/kevin/ws_cloud/Programme Python/WNodePython/external_modules/" ./