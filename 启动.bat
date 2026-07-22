@echo off
title LaienTech - App Review Analyzer
cd /d "%~dp0"

echo === Step 1: Python ===
python --version
if errorlevel 1 ( echo Python not found! Install Python 3.10+ && pause && exit )
echo OK

echo === Step 2: Node ===
node --version
if errorlevel 1 ( echo Node not found! Install Node.js && pause && exit )
echo OK

echo === Step 3: Dependencies ===
cd backend
pip install -r requirements.txt >nul 2>&1
cd ..

if not exist "frontend\node_modules" (
    cd frontend
    call npm install
    cd ..
)

echo === Step 4: Start Backend ===
start "Backend" /D "%~dp0backend" python main.py
timeout /t 5 /nobreak >nul

echo === Step 5: Start Frontend ===
start "Frontend" /D "%~dp0frontend" npx vite --host
timeout /t 3 /nobreak >nul

start http://localhost:3000
echo Done! http://localhost:3000
pause
