@echo off
setlocal enabledelayedexpansion

echo.
echo  ==========================================
echo   Producthuntbasic - Product Hunt Research
echo  ==========================================
echo.

:: -----------------------------------------------
:: STEP 1: Check if Python is available in PATH
:: -----------------------------------------------
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Python found in PATH
    set "PYTHON_CMD=python"
    goto :check_venv
)

where python3 >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Python3 found in PATH
    set "PYTHON_CMD=python3"
    goto :check_venv
)

:: -----------------------------------------------
:: STEP 2: Check for local embedded Python
:: -----------------------------------------------
if exist ".python\python.exe" (
    echo  [OK] Local Python found in .python\
    set "PYTHON_CMD=.python\python.exe"
    goto :check_venv
)

:: -----------------------------------------------
:: STEP 3: Download Python 3.11.9 embedded package
:: -----------------------------------------------
echo.
echo  Python not found. Downloading Python 3.11.9 (embedded)...
echo  This is a one-time setup (~8 MB download).
echo.

:: Create .python directory
if not exist ".python" mkdir ".python"

:: Download Python embedded zip
echo  Downloading...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile '.python\python-embed.zip'}" 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Download failed. Please install Python 3.11+ manually from https://www.python.org
    echo  Then run this script again.
    pause
    exit /b 1
)

:: Extract Python
echo  Extracting...
powershell -Command "Expand-Archive -Path '.python\python-embed.zip' -DestinationPath '.python' -Force" 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Extraction failed.
    pause
    exit /b 1
)

:: Clean up zip
del ".python\python-embed.zip" >nul 2>&1

:: Enable site-packages by uncommenting import site in python311._pth
echo  Configuring Python...
powershell -Command "$f = Get-ChildItem '.python\python*._pth' | Select-Object -First 1; if ($f) { $c = Get-Content $f.FullName -Raw; $c = $c -replace '#import site', 'import site'; Set-Content $f.FullName $c }" 2>nul

:: Download get-pip.py
echo  Installing pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '.python\get-pip.py'}" 2>nul
if %errorlevel% neq 0 (
    echo  [ERROR] Could not download pip installer.
    pause
    exit /b 1
)

:: Install pip
.python\python.exe .python\get-pip.py --no-warn-script-location >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] pip installation failed.
    pause
    exit /b 1
)

del ".python\get-pip.py" >nul 2>&1

echo  [OK] Python 3.11.9 installed locally
set "PYTHON_CMD=.python\python.exe"

:: -----------------------------------------------
:: STEP 4: Setup virtual environment
:: -----------------------------------------------
:check_venv
echo.

if not exist ".venv" (
    echo  Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo  [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created
)

:: Use venv Python from now on
set "VENV_PYTHON=.venv\Scripts\python.exe"

:: -----------------------------------------------
:: STEP 5: Install dependencies
:: -----------------------------------------------
%VENV_PYTHON% -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Installing dependencies (first run)...
    .venv\Scripts\pip.exe install -r requirements.txt --no-warn-script-location >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo  [OK] Dependencies installed
) else (
    echo  [OK] Dependencies already installed
)

:: -----------------------------------------------
:: STEP 6: Start the application
:: -----------------------------------------------
echo.
echo  ==========================================
echo   Starting Producthuntbasic...
echo   Open http://127.0.0.1:8000
echo  ==========================================
echo.
echo  Press Ctrl+C to stop the server.
echo.

.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

pause
