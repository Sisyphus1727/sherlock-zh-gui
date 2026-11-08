@echo off
rem Sherlock launcher - works from any working directory.
rem Usage: sherlock.cmd <username> [options]
rem Output files (txt/csv/xlsx) are written to the CURRENT directory.
rem Uses .venv if present, otherwise falls back to "python" on PATH.
setlocal
set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"
set "PYTHONPATH=%REPO%"
set "PY=%REPO%\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m sherlock_project %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
