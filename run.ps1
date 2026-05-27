# Simple Signal CLI - PowerShell Launcher
# This script runs the AI CLI with optional model path

$MODEL_PATH = $env:MODEL_PATH

if ($MODEL_PATH) {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "🎯 Starting Simple Signal AI with model: $MODEL_PATH" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    python ai_cli.py "$MODEL_PATH" --skip-selector
} else {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "🚀 Starting Simple Signal AI..." -ForegroundColor Yellow
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "🎯 NEW FEATURE: Model Selector is enabled!" -ForegroundColor Green
    Write-Host "    If LM Studio is running, you'll see an interactive menu." -ForegroundColor Green
    Write-Host "    Just pick a number to select your model!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Cyan
    python ai_cli.py
}
