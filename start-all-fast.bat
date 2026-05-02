@echo off
chcp 65001 >nul

echo ========================================
echo BTC Quant 快速启动
echo ========================================
echo.

echo [1/2] 启动后端服务...
start "BTC Quant Backend" cmd /k "c:\LH\OKX\start-backend-fast.bat"

echo [2/2] 启动前端服务...
start "BTC Quant Frontend" cmd /k "c:\LH\OKX\start-frontend-fast.bat"

echo.
echo ========================================
echo 启动完成！
echo ========================================
echo.
echo 访问地址：
echo   - 后端API: http://localhost:8000
echo   - 前端界面: http://localhost:5173
echo.
echo 提示：两个窗口会自动打开，请保持运行
echo.
pause
