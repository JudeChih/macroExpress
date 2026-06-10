@echo off
chcp 65001 >nul
title Macro Auto Clicker Launcher
cd /d "%~dp0"

echo ============================================
echo   Macro Auto Clicker - Starting
echo ============================================
echo.

REM --- Step 1: locate Python ---
set "PYCMD="
where python >nul 2>nul && set "PYCMD=python"
if not defined PYCMD (
    where py >nul 2>nul && set "PYCMD=py"
)

if not defined PYCMD (
    echo [ERROR] Python not found.
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo During install, CHECK the box "Add Python to PATH".
    echo Then double-click this file again.
    echo.
    pause
    exit /b
)

echo Using Python command: %PYCMD%
%PYCMD% --version
echo.

REM --- Step 2: ensure pynput is installed ---
%PYCMD% -c "import pynput" 2>nul
if errorlevel 1 (
    echo Installing dependency: pynput ...
    %PYCMD% -m pip install pynput
    echo.
)

REM --- Step 3: launch the app ---
echo Launching... (a window should appear)
%PYCMD% macro_clicker.py

echo.
echo ============================================
echo  Program ended. If you see a red error above,
echo  take a screenshot and send it to me.
echo ============================================
pause
