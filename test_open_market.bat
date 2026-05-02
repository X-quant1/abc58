@echo off
echo ========================================
echo   测试开多单 - 0.01张 BTC-USDT-SWAP
echo ========================================
echo.

cd /d C:\LH\OKX\tools\node-v20.18.0-win-x64

echo [1] 获取当前价格...
okx market ticker BTC-USDT-SWAP
echo.

echo [2] 设置杠杆为100x（全仓）...
okx swap leverage --instId BTC-USDT-SWAP --lever 100 --mgnMode cross --posSide long
echo.

echo [3] 开多单 0.01张（市价单）...
okx swap place --instId BTC-USDT-SWAP --side buy --ordType market --sz 0.01 --posSide long --tdMode cross
echo.

echo [4] 查询持仓...
okx swap positions --instId BTC-USDT-SWAP
echo.

echo ========================================
echo   测试完成！
echo ========================================
pause
