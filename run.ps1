# Simple Signal CLI - PowerShell Launcher
# This script runs the AI CLI with optional model path

$MODEL_PATH = $env:MODEL_PATH

if ($MODEL_PATH) {
    Write-Host "Starting Simple Signal AI with model: $MODEL_PATH" -ForegroundColor Cyan
    python ai_cli.py "$MODEL_PATH"
} else {
    Write-Host "Starting Simple Signal AI in demo mode..." -ForegroundColor Yellow
    python ai_cli.py
}
