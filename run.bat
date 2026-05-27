@echo off
REM Simple Signal CLI - Windows Launcher
REM This script runs the AI CLI with optional model path

setlocal

REM Check if MODEL_PATH environment variable is set
if defined MODEL_PATH (
    echo Starting Simple Signal AI with model: %MODEL_PATH%
    python ai_cli.py "%MODEL_PATH%"
) else (
    echo Starting Simple Signal AI in demo mode...
    python ai_cli.py
)

endlocal

pause
