@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -3 -m venv .venv
    if errorlevel 1 goto failed
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Starting DalasiFX. Open http://127.0.0.1:5000 in your browser.
echo Press Ctrl+C to stop the server.
python app.py
exit /b %errorlevel%
:failed
echo Setup failed. Make sure Python 3.9 or newer is installed and available as 'py'.
pause
exit /b 1
