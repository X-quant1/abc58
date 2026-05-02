@echo off
set PATH=C:\LH\OKX\tools\node-v20.18.0-win-x64;%PATH%
cd /d C:\LH\OKX
C:\LH\OKX\tools\node-v20.18.0-win-x64\node.exe -e "const puppeteer = require('puppeteer'); (async () => { const b = await puppeteer.launch({headless: false}); console.log('Browser launched'); await (await b.newPage()).goto('https://www.okx.com'); })();"
