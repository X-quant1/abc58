@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   测试开多单 - 带止盈止损和移动止盈
echo ========================================
echo.

cd /d C:\LH\OKX\tools\node-v20.18.0-win-x64

REM 参数设置
set INST_ID=BTC-USDT-SWAP
set SZ=0.01
set LEVERAGE=100
set TP_PCT=60
set SL_PCT=35
set TRAIL_ACTIVATE_PCT=50
set TRAIL_CALLBACK_POINTS=25

echo [参数]
echo   合约: %INST_ID%
echo   张数: %SZ%
echo   杠杆: %LEVERAGE%x
echo   止盈: %TP_PCT%% (杠杆收益)
echo   止损: %SL_PCT%% (杠杆亏损)
echo   移动止盈激活: %TRAIL_ACTIVATE_PCT%% (杠杆收益)
echo   移动止盈回调: %TRAIL_CALLBACK_POINTS%点
echo.

echo [1] 获取当前价格...
for /f "tokens=2 delims=:" %%a in ('okx market ticker BTC-USDT-SWAP ^| findstr "last"') do (
    set CURRENT_PRICE=%%a
    set CURRENT_PRICE=!CURRENT_PRICE:"=!
    set CURRENT_PRICE=!CURRENT_PRICE:,=!
    set CURRENT_PRICE=!CURRENT_PRICE: =!
)
echo   当前价格: $%CURRENT_PRICE%
echo.

REM 计算止盈止损价位（百分比需要除以杠杆）
REM 止盈价 = 当前价 * (1 + TP_PCT/LEVERAGE/100)
REM 止损价 = 当前价 * (1 - SL_PCT/LEVERAGE/100)

REM 使用PowerShell计算
for /f %%i in ('powershell -command "[math]::Round(%CURRENT_PRICE% * (1 + %TP_PCT% / %LEVERAGE% / 100), 2)"') do set TP_PRICE=%%i
for /f %%i in ('powershell -command "[math]::Round(%CURRENT_PRICE% * (1 - %SL_PCT% / %LEVERAGE% / 100), 2)"') do set SL_PRICE=%%i
for /f %%i in ('powershell -command "[math]::Round(%CURRENT_PRICE% * (1 + %TRAIL_ACTIVATE_PCT% / %LEVERAGE% / 100), 2)"') do set ACTIVATE_PRICE=%%i

echo [2] 计算止盈止损价位...
echo   止盈触发价: $%TP_PRICE%
echo   止损触发价: $%SL_PRICE%
echo   移动止盈激活价: $%ACTIVATE_PRICE%
echo.

echo [3] 设置杠杆为 %LEVERAGE%x（全仓）...
okx swap leverage --instId %INST_ID% --lever %LEVERAGE% --mgnMode cross --posSide long
echo.

echo [4] 开多单 %SZ%张（带止盈止损）...
okx swap place --instId %INST_ID% --side buy --ordType market --sz %SZ% --posSide long --tdMode cross --tpTriggerPx %TP_PRICE% --tpOrdPx=-1 --slTriggerPx %SL_PRICE% --slOrdPx=-1
echo.

echo [5] 设置移动止盈算法单...
okx swap algo --instId %INST_ID% --ordType move_order_stop --side sell --sz %SZ% --posSide long --tdMode cross --callbackValue %TRAIL_CALLBACK_POINTS% --activatePx %ACTIVATE_PRICE%
echo.

echo [6] 查询持仓和算法单...
okx swap positions --instId %INST_ID%
echo.
okx swap orders-algo --instId %INST_ID%
echo.

echo ========================================
echo   测试完成！请检查OKX后台
echo ========================================
pause
