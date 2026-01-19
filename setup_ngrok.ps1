# Setup script for ngrok authentication
Write-Host "🔧 ngrok Setup for Smiley's Blog" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

Write-Host "Step 1: Get your ngrok token" -ForegroundColor Yellow
Write-Host "1. Go to: https://dashboard.ngrok.com" -ForegroundColor Cyan
Write-Host "2. Login to your account" -ForegroundColor Cyan
Write-Host "3. Copy your authtoken" -ForegroundColor Cyan
Write-Host ""

# Prompt for token
$token = Read-Host "Paste your ngrok authtoken here"

if ($token) {
    Write-Host ""
    Write-Host "🔑 Adding token to ngrok..." -ForegroundColor Yellow
    
    try {
        $result = .\ngrok.exe config add-authtoken $token 2>&1
        Write-Host "✅ Token added successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "🚀 You can now run: share_with_ngrok.ps1" -ForegroundColor Green
        Write-Host ""
        
        # Test the connection
        Write-Host "🧪 Testing ngrok..." -ForegroundColor Yellow
        $testResult = .\ngrok.exe config check 2>&1
        if ($testResult -match "OK") {
            Write-Host "✅ ngrok is ready to use!" -ForegroundColor Green
        } else {
            Write-Host "⚠️  ngrok setup complete, but test failed. Try running share_with_ngrok.ps1" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "❌ Error adding token: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Try running manually: .\ngrok.exe config add-authtoken $token" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ No token provided. Please run this script again with your token." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")