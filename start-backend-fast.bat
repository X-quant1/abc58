@echo off
chcp 65001 >nul
title BTC Quant Backend

echo 启动后端服务...
cd /d c:\LH\OKX\backend

C:\Users\Administrator\.workbuddy\binaries\python\envs\btc-quant\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
