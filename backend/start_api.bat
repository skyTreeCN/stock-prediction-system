@echo off
REM Set UTF-8 encoding for Python
set PYTHONIOENCODING=utf-8

REM Activate virtual environment and start API
cd /d %~dp0
call venv\Scripts\activate.bat
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
