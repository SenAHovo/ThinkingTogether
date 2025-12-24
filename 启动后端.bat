@echo off
chcp 65001 > nul
echo ====================================
echo 智炬五维协同学习系统 - 后端启动
echo ====================================
echo.

:: 检查端口占用
echo 检查端口8000是否被占用...
netstat -ano | findstr "8000" | findstr "LISTENING" > nul
if %errorlevel% == 0 (
    echo.
    echo 警告: 端口8000已被占用！
    echo 正在尝试释放端口...
    echo.
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr "8000" ^| findstr "LISTENING"') do (
        echo 终止进程 %%a...
        taskkill /PID %%a /F > nul 2>&1
    )
    timeout /t 2 /nobreak > nul
)

echo 启动后端服务...
echo 端口: 8000
echo API文档: http://localhost:8000/docs
echo 健康检查: http://localhost:8000/api/health
echo.
echo 按 Ctrl+C 停止服务
echo ====================================
echo.

python -m uvicorn dev.api.server:app --host 0.0.0.0 --port 8000 --log-level info

pause
