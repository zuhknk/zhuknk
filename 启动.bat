@echo off
title LaienTech - App Review Analyzer
set "ROOT=%~dp0"

echo.
echo   ==========================================
echo     LaienTech iOS App Review Analyzer
echo   ==========================================
echo.

:: --- 1. Python ---
echo   [1/4] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [X] Python not found. Install Python 3.10+
    echo   [X] https://www.python.org/downloads/
    goto end
)
python --version
echo   [OK]

:: --- 2. Node ---
echo   [2/4] Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo   [X] Node.js not found. Install Node.js
    echo   [X] https://nodejs.org/
    goto end
)
node --version
echo   [OK]

:: --- 3. .env ---
echo   [3/4] Config...
if not exist "%ROOT%.env" (
    if exist "%ROOT%.env.example" (
        copy "%ROOT%.env.example" "%ROOT%.env" >nul
        echo   Copied from .env.example
    )
) else ( echo   [OK] )

:: --- 4. Dependencies ---
echo   [4/4] Dependencies...
cd /d "%ROOT%backend"
pip install -r requirements.txt >nul 2>&1
cd /d "%ROOT%"

if not exist "%ROOT%frontend\node_modules" (
    echo   Installing frontend deps...
    cd /d "%ROOT%frontend"
    call npm install
    cd /d "%ROOT%"
)

echo.
echo   Starting services...
echo.

:: 后端 — 用 cmd /k 保持窗口打开（可以看到报错）
start "Backend-8000" cmd /k "cd /d "%ROOT%backend" && echo Backend: http://localhost:8000 && python main.py"
timeout /t 4 /nobreak >nul

:: 前端 — 同上
start "Frontend-3000" cmd /k "cd /d "%ROOT%frontend" && echo Frontend: http://localhost:3000 && npx vite --host"
timeout /t 4 /nobreak >nul

:: 打开浏览器
start http://localhost:3000

echo.
echo   ==========================================
echo   Done! http://localhost:3000
echo   Close this window to stop all services
echo   ==========================================
echo.

:end
pause