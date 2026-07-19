@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo == HashSieve local venv launcher ==
echo IMPORTANT: For drag-and-drop from File Explorer, do NOT run this terminal as Administrator.
echo.

set "VENV_DIR=.venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating local virtual environment...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create local virtual environment.
        pause
        exit /b 1
    )
)
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

set "QT_PLUGIN_PATH="
set "QML2_IMPORT_PATH="
set "PYTHONPATH="
set "PYSIDE_DESIGNER_PLUGINS="

"%PY_EXE%" -c "from PySide6.QtCore import Qt; import send2trash" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    "%PY_EXE%" -m pip install --upgrade pip
    if errorlevel 1 goto DEP_FAIL
    "%PY_EXE%" -m pip install --upgrade -r requirements.txt
    if errorlevel 1 goto DEP_FAIL
)

echo Starting HashSieve...
"%PY_EXE%" main.py
if errorlevel 1 pause
exit /b %errorlevel%

:DEP_FAIL
echo Dependency installation failed.
pause
exit /b 1
