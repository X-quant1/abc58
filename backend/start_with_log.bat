@echo off
cd /d c:\LH\OKX\backend
C:\Users\Administrator\.workbuddy\binaries\python\envs\btc-quant\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1
