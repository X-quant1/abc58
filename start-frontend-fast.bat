@echo off
chcp 65001 >nul
title BTC Quant Frontend

echo 启动前端服务...
cd /d c:\LH\OKX\frontend

npm run dev
