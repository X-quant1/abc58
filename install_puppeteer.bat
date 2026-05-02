@echo off
set PATH=C:\LH\OKX\tools\node-v20.18.0-win-x64;%PATH%
cd /d C:\LH\OKX
set npm_config_node_path=C:\LH\OKX\tools\node-v20.18.0-win-x64
set npm_config_prefix=C:\LH\OKX\tools\node-v20.18.0-win-x64
C:\LH\OKX\tools\node-v20.18.0-win-x64\npm.cmd install puppeteer --ignore-scripts
