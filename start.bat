@echo off
echo Starting BTC Quant services...

REM Kill existing processes
taskkill /F /IM node.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

REM Start backend
cd /d c:\LH\OKX\backend
start "BTC Quant Backend" C:\Users\Administrator\.workbuddy\binaries\python\envs\btc-quant\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

REM Wait for backend
timeout /t 3 /nobreak >nul

REM Start frontend
cd /d c:\LH\OKX\frontend
start "BTC Quant Frontend" C:\LH\OKX\tools\node-v20.18.0-win-x64\node.exe node_modules\vite\bin\vite.js

echo.
echo Services started!
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
pause
