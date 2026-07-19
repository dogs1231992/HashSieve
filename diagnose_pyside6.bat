@echo off
setlocal
cd /d "%~dp0"
echo == HashSieve PySide6 diagnostic ==
echo.
echo Current Python:
python -c "import sys; print(sys.executable); print(sys.version)"
echo.
echo Installed Qt/PySide packages:
python -m pip show PySide6 shiboken6 PySide6-Essentials PySide6-Addons 2>nul
echo.
echo Import test:
python -c "from PySide6.QtCore import Qt; from PySide6.QtWidgets import QApplication; print('PySide6 import OK')"
echo.
pause
