@echo off
echo ========================================
echo 股票预测系统 - 后端启动脚本
echo ========================================
echo.

REM 检查是否存在 venv 目录
if exist venv (
    echo 检测到 venv 环境，正在激活...
    call venv\Scripts\activate.bat
) else (
    echo 检测到 conda 环境，正在激活...
    call conda activate stock-prediction
)

echo.
echo 启动 FastAPI 服务器...
echo 访问地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
