@echo off
title Ritesh AI Call Assistant Automated Verification Suite
cd /d "%~dp0backend"
echo ==============================================================================
echo       RITESH AI CALL ASSISTANT — RUNNING COMPLETE AUTOMATION SUITE
echo ==============================================================================
echo.
".venv\Scripts\python.exe" -u tests\test_automated_suite.py
echo.
pause
