@echo off
echo ================================
echo   BTC Quant - Start Frontend
echo ================================
cd /d c:\LH\OKX\frontend
set PATH=c:\LH\OKX\tools\node-v20.18.0-win-x64;%PATH%
npx vite --host 0.0.0.0 --port 5173
