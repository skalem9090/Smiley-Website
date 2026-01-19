@echo off
echo Starting Smiley's Blog for external access...
echo.

REM Set environment variables from .env file
echo Loading environment variables...
set SECRET_KEY=85f58c823f8812dd4d4d24250b9e278900d3744e566ef92a97514ea6dbf64feb
set FLASK_ENV=production
set DATABASE_URL=sqlite:///C:\Users\skale\OneDrive\Desktop\SmileyWebsite\Smiley-Website\instance\site.db
set UPLOAD_FOLDER=static/uploads

REM Start the Flask app in the background
echo Starting Flask application...
start /B python app.py

REM Wait a moment for Flask to start
echo Waiting for Flask to start...
timeout /t 5 /nobreak >nul

REM Start ngrok tunnel
echo Starting ngrok tunnel...
echo.
echo Your blog will be accessible at the ngrok URL shown below:
echo Share this URL with the developer to test your blog!
echo.
echo Press Ctrl+C to stop both services when done.
echo.

ngrok http 5000