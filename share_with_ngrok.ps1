# PowerShell script to share Smiley's Blog with ngrok
Write-Host "🚀 Starting Smiley's Blog for external access..." -ForegroundColor Green
Write-Host ""

# Check if ngrok is authenticated
Write-Host "🔑 Checking ngrok authentication..." -ForegroundColor Yellow
$authCheck = .\ngrok.exe config check 2>&1
if ($authCheck -match "authtoken") {
    Write-Host "✅ ngrok is authenticated!" -ForegroundColor Green
} else {
    Write-Host "❌ ngrok needs authentication!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run this command first:" -ForegroundColor Yellow
    Write-Host ".\ngrok.exe config add-authtoken YOUR_TOKEN_HERE" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Get your token from: https://dashboard.ngrok.com" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter after adding your token"
}

# Set environment variables
Write-Host "📄 Setting environment variables..." -ForegroundColor Yellow
$env:SECRET_KEY = "85f58c823f8812dd4d4d24250b9e278900d3744e566ef92a97514ea6dbf64feb"
$env:FLASK_ENV = "production"
$env:DATABASE_URL = "sqlite:///C:\Users\skale\OneDrive\Desktop\SmileyWebsite\Smiley-Website\instance\site.db"
$env:UPLOAD_FOLDER = "static/uploads"

# Start Flask app in background
Write-Host "🌐 Starting Flask application..." -ForegroundColor Yellow
$flaskProcess = Start-Process -FilePath "python" -ArgumentList "app.py" -PassThru -WindowStyle Hidden

# Wait for Flask to start
Write-Host "⏳ Waiting for Flask to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if Flask is running
$flaskRunning = Get-Process -Id $flaskProcess.Id -ErrorAction SilentlyContinue
if ($flaskRunning) {
    Write-Host "✅ Flask is running!" -ForegroundColor Green
} else {
    Write-Host "❌ Flask failed to start!" -ForegroundColor Red
    exit 1
}

# Start ngrok
Write-Host ""
Write-Host "🌍 Starting ngrok tunnel..." -ForegroundColor Green
Write-Host "Your blog will be accessible at the ngrok URL shown below:" -ForegroundColor Cyan
Write-Host "Share this URL with the developer to test your blog!" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop both services when done." -ForegroundColor Yellow
Write-Host ""

# Run ngrok (this will block until stopped)
try {
    .\ngrok.exe http 5000
} finally {
    # Cleanup: Stop Flask when ngrok stops
    Write-Host ""
    Write-Host "🛑 Stopping Flask application..." -ForegroundColor Yellow
    Stop-Process -Id $flaskProcess.Id -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Cleanup complete!" -ForegroundColor Green
}