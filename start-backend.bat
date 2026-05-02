@echo off
echo ================================
echo   BTC Quant - Start Backend
echo ================================
cd /d c:\LH\OKX\backend
C:\Users\Administrator\.workbuddy\binaries\python\envs\btc-quant\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
