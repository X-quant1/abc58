@echo off
set PATH=C:\LH\OKX\tools\node-v20.18.0-win-x64;%PATH%
set PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=false
cd /d C:\LH\OKX
C:\LH\OKX\tools\node-v20.18.0-win-x64\node.exe node_modules\puppeteer\lib\esm\puppeteer\node\install.js
