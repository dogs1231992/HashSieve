@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo == HashSieve isolated conda launcher ==
echo This launcher avoids PySide6/Qt DLL conflicts from the Anaconda base environment.
echo.

echo IMPORTANT: For drag-and-drop from File Explorer, do NOT run this terminal as Administrator.
echo Windows blocks drag-and-drop from a normal Explorer window into an elevated app.
echo.

set "ENV_NAME=hashsieve-gui"

where conda >nul 2>nul
if errorlevel 1 (
    echo Conda was not found in PATH. Falling back to run_clean_venv.bat...
    call run_clean_venv.bat
    exit /b %errorlevel%
)

call conda info --envs | findstr /R /C:"^[ ]*%ENV_NAME%[ ]" >nul 2>nul
if errorlevel 1 (
    echo Creating conda environment: %ENV_NAME%
    call conda create -y -n %ENV_NAME% python=3.11 pip
    if errorlevel 1 (
        echo Failed to create conda environment.
        pause
        exit /b 1
    )
)

set "QT_PLUGIN_PATH="
set "QML2_IMPORT_PATH="
set "PYTHONPATH="
set "PYSIDE_DESIGNER_PLUGINS="

echo Checking dependencies...
call conda run -n %ENV_NAME% python -c "from PySide6.QtCore import Qt; import send2trash" >nul 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    call conda run -n %ENV_NAME% python -m pip install --upgrade pip
    if errorlevel 1 goto DEP_FAIL
    call conda run -n %ENV_NAME% python -m pip install --upgrade -r requirements.txt
    if errorlevel 1 goto DEP_FAIL
)

echo Starting HashSieve...
call conda run -n %ENV_NAME% python main.py
if errorlevel 1 pause
exit /b %errorlevel%

:DEP_FAIL
echo Dependency installation failed.
pause
exit /b 1
