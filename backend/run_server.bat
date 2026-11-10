@echo off
title Ritesh AI Call Assistant Server
echo ======================================================================
echo           Starting Ritesh AI Call Assistant Backend Server
echo ======================================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\uvicorn.exe" (
    echo Error: .venv not found. Please run: python -m venv .venv
    pause
    exit /b 1
)
echo Server starting at http://127.0.0.1:8000
echo Swagger UI Docs: http://127.0.0.1:8000/docs
echo.
".venv\Scripts\uvicorn.exe" app.main:app --host 0.0.0.0 --port 8000 --reload
pause
