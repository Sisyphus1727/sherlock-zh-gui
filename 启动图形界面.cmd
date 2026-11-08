@echo off
rem Sherlock GUI launcher - Chinese web interface.
rem Double-click this file. Close the black window to quit.
rem Uses .venv if present, otherwise falls back to "python" on PATH.
setlocal
chcp 65001 >nul
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "PYTHONPATH=%REPO%"
set "PYTHONIOENCODING=utf-8"
set "PY=%REPO%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
title Sherlock GUI (close this window to exit)
"%PY%" "%REPO%\gui\server.py"
set "RC=%ERRORLEVEL%"
echo.
echo Program exited with code %RC%.
pause
