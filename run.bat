@echo off
REM Simple Signal CLI - Windows Launcher
REM This script runs the AI CLI with optional model path

setlocal

REM Check if MODEL_PATH environment variable is set
if defined MODEL_PATH (
    echo ========================================
    echo 🎯 Starting Simple Signal AI with model: %MODEL_PATH%
    echo ========================================
    python ai_cli.py "%MODEL_PATH%" --skip-selector
) else (
    echo ========================================
    echo 🚀 Starting Simple Signal AI...
    echo ========================================
    echo 🎯 NEW FEATURE: Model Selector is enabled!
    echo    If LM Studio is running, you'll see an interactive menu.
    echo    Just pick a number to select your model!
    echo ========================================
    python ai_cli.py
)

endlocal

pause
