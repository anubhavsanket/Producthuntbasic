@echo off
echo ==========================================
echo   Product Hunt Research Console
echo ==========================================
echo.
echo Starting the application...
echo Open http://127.0.0.1:8000 in your browser
echo.
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
