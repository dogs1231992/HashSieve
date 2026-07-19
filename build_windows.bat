@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo == HashSieve Windows EXE build ==
echo Project: %CD%

echo.
echo [1/5] Preparing isolated build environment...
set "ENV_NAME=hashsieve-gui-build"
set "USE_CONDA=0"
set "PY_EXE="

where conda >nul 2>nul
if not errorlevel 1 (
    set "USE_CONDA=1"
    call conda info --envs | findstr /R /C:"^[ ]*%ENV_NAME%[ ]" >nul 2>nul
    if errorlevel 1 (
        echo Creating build conda environment: %ENV_NAME%
        call conda create -y -n %ENV_NAME% python=3.11 pip
        if errorlevel 1 goto VENV_FALLBACK
    )
    goto INSTALL_DEPS
)

:VENV_FALLBACK
echo Conda build environment unavailable. Using local .build_venv instead.
set "USE_CONDA=0"
set "VENV_DIR=.build_venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create build virtual environment.
        pause
        exit /b 1
    )
)
set "PY_EXE=%VENV_DIR%\Scripts\python.exe"

:INSTALL_DEPS
echo.
echo [2/5] Installing dependencies...
set "QT_PLUGIN_PATH="
set "QML2_IMPORT_PATH="
set "PYTHONPATH="
set "PYSIDE_DESIGNER_PLUGINS="

if "%USE_CONDA%"=="1" (
    call conda run -n %ENV_NAME% python -m pip install --upgrade pip
    if errorlevel 1 goto INSTALL_FAIL
    call conda run -n %ENV_NAME% python -m pip install --upgrade -r requirements.txt
    if errorlevel 1 goto INSTALL_FAIL
    call conda run -n %ENV_NAME% python -c "from PySide6.QtCore import Qt; import send2trash; import PyInstaller; print('Build dependency check OK')"
    if errorlevel 1 goto INSTALL_FAIL
) else (
    "%PY_EXE%" -m pip install --upgrade pip
    if errorlevel 1 goto INSTALL_FAIL
    "%PY_EXE%" -m pip install --upgrade -r requirements.txt
    if errorlevel 1 goto INSTALL_FAIL
    "%PY_EXE%" -c "from PySide6.QtCore import Qt; import send2trash; import PyInstaller; print('Build dependency check OK')"
    if errorlevel 1 goto INSTALL_FAIL
)

echo.
echo [3/5] Building one-file EXE with PyInstaller...
if "%USE_CONDA%"=="1" (
    call conda run -n %ENV_NAME% python -m PyInstaller HashSieve.spec --noconfirm --clean
    if errorlevel 1 goto BUILD_FAIL
) else (
    "%PY_EXE%" -m PyInstaller HashSieve.spec --noconfirm --clean
    if errorlevel 1 goto BUILD_FAIL
)

echo.
echo [4/5] Copying EXE and generating checksums...
if not exist release mkdir release
copy /Y dist\HashSieve.exe release\HashSieve.exe >nul
if errorlevel 1 goto BUILD_FAIL
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-FileHash release\HashSieve.exe -Algorithm SHA256 | ForEach-Object { 'SHA256  ' + $_.Hash.ToLower() + '  HashSieve.exe' } | Set-Content release\HashSieve.exe.sha256 -Encoding ascii; Get-FileHash release\HashSieve.exe -Algorithm SHA512 | ForEach-Object { 'SHA512  ' + $_.Hash.ToLower() + '  HashSieve.exe' } | Set-Content release\HashSieve.exe.sha512 -Encoding ascii; Get-Content release\HashSieve.exe.sha256,release\HashSieve.exe.sha512 | Set-Content release\CHECKSUMS.txt -Encoding ascii"
if errorlevel 1 goto BUILD_FAIL

echo.
echo [5/5] Cleaning temporary build files...
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul
rmdir /S /Q .build_venv 2>nul
for /d /r %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo.
echo Build complete.
echo EXE: %CD%\release\HashSieve.exe
echo Checksums: %CD%\release\CHECKSUMS.txt
echo.
echo IMPORTANT: For drag-and-drop from File Explorer, launch HashSieve normally.
echo Do not run the EXE or PowerShell as Administrator unless File Explorer is also elevated.
pause
exit /b 0

:INSTALL_FAIL
echo.
echo Dependency installation or import check failed.
echo Try deleting the build environment and running this script again:
echo   conda env remove -n %ENV_NAME%
echo   .\build_windows.bat
pause
exit /b 1

:BUILD_FAIL
echo.
echo PyInstaller build failed.
echo Please copy the full console output and send it with your log.
pause
exit /b 1
