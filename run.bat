@echo off
REM Simple Signal CLI - Windows Launcher
REM This script runs the Electron Desktop App wrapper

setlocal

echo ========================================
echo 🚀 Starting Simple Signal Desktop App...
echo ========================================

cd desktop
if not exist "node_modules\" (
    echo Installing Desktop App dependencies...
    call npm install
)
call npm start

endlocal
pause
