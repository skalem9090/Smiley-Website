@echo off
echo Starting Smileys Blog Site Production Server...
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Start the production server
python start_production.py

pause