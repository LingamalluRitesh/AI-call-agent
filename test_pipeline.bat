@echo off
title Ritesh AI Call Assistant Test Harness
cd /d "%~dp0backend"
if "%~1"=="" (
    ".venv\Scripts\python.exe" simulate_call.py
) else (
    ".venv\Scripts\python.exe" simulate_call.py %*
)
echo.
pause
