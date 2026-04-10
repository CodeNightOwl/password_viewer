@echo off
cd /d "%~dp0"
echo Building...
python -m PyInstaller --onefile --windowed --name "ÐÇºÅÌ½²âÆ÷-Owl" --icon "icon.ico" --add-data "hook_reader.dll;." --add-data "hook_reader32.dll;." --add-data "load_hook32.exe;." --add-data "load_hook64.exe;." --add-data "ÐÇºÅ.png;." --clean password_viewer.py
if %ERRORLEVEL% EQU 0 (
echo Build OK
) else (
echo Build FAILED
)
pause

