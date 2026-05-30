# Simple Signal CLI - PowerShell Launcher
# This script runs the Electron Desktop App wrapper

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "🚀 Starting Simple Signal Desktop App..." -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

Set-Location "desktop"
if (!(Test-Path "node_modules")) {
    Write-Host "Installing Desktop App dependencies..." -ForegroundColor Green
    npm install
}
npm start
