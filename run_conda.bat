@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set VENV_DIR=.venv
set PY_EXE=%VENV_DIR%\Scripts\python.exe

if not exist "%PY_EXE%" (
    echo Creating local virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv "%VENV_DIR%"
    ) else (
        where python >nul 2>nul
        if not errorlevel 1 (
            python -m venv "%VENV_DIR%"
        ) else (
            where python3 >nul 2>nul
            if not errorlevel 1 (
                python3 -m venv "%VENV_DIR%"
            ) else (
                echo Failed to find Python. Install Python 3.10+ or run from Anaconda/Miniconda Prompt.
                pause
                exit /b 1
            )
        )
    )
    if errorlevel 1 (
        echo Failed to create virtual environment. Make sure Python 3 is installed.
        pause
        exit /b 1
    )
)

"%PY_EXE%" -m pip install --upgrade pip
"%PY_EXE%" -m pip install --prefer-binary -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

"%PY_EXE%" main.py
pause
