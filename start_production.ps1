# PowerShell script to start Smileys Blog Site Production Server

Write-Host "🚀 Starting Smileys Blog Site Production Server..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Start the production server
try {
    python start_production.py
}
catch {
    Write-Host "❌ Error starting server: $_" -ForegroundColor Red
    Read-Host "Press Enter to continue..."
}