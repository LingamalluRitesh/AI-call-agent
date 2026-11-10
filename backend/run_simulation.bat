@echo off
title Ritesh AI Call Simulator
echo ======================================================================
echo              Ritesh AI Call Assistant Simulator
echo ======================================================================
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Error: .venv not found.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" simulate_call.py
echo.
pause
