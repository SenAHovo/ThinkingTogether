@echo off
chcp 65001 > nul
echo ====================================
echo 智炬五维协同学习系统 - 前端启动
echo ====================================
echo.

cd /d "%~dp0FrontDev"

echo 检查依赖是否已安装...
if not exist "node_modules\" (
    echo 首次运行，正在安装依赖...
    call npm install
    echo.
)

echo 启动前端开发服务器...
echo 默认端口: 5173 (Vite会自动选择可用端口)
echo.
echo 按 Ctrl+C 停止服务
echo ====================================
echo.

call npm run dev

pause
