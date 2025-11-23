@echo off
REM ============================================================
REM   AI Comic Book Generator - Start All Services
REM   For Windows
REM ============================================================

echo.
echo ============================================================
echo   Starting AI Comic Book Generator Services
echo ============================================================
echo.

REM Change to your project directory
cd /d E:\AiComic\comic_generator

REM Set Python path
set PYTHON=E:\AiComic\venv\Scripts\python.exe

REM Create output directories
if not exist "output" mkdir output
if not exist "logs" mkdir logs

echo [1/6] Starting Scene Generator (Port 8001)...
start "Scene Generator - Port 8001" /MIN cmd /k "%PYTHON% scene_generator.py"
timeout /t 3 /nobreak >nul

echo [2/6] Starting Image Generator (Port 8002)...
start "Image Generator - Port 8002" /MIN cmd /k "%PYTHON% image_generator.py"
timeout /t 3 /nobreak >nul

echo [3/6] Starting Bubble Placement (Port 8003)...
start "Bubble Placement - Port 8003" /MIN cmd /k "%PYTHON% bubble_placement.py"
timeout /t 3 /nobreak >nul

echo [4/6] Starting Dialogue Generator (Port 8004)...
start "Dialogue Generator - Port 8004" /MIN cmd /k "%PYTHON% dialogue_generator.py"
timeout /t 3 /nobreak >nul

echo [5/6] Starting Bubble Renderer (Port 8005)...
start "Bubble Renderer - Port 8005" /MIN cmd /k "%PYTHON% bubble_renderer.py"
timeout /t 3 /nobreak >nul

echo [6/6] Starting Main Orchestrator (Port 8000)...
start "Main Orchestrator - Port 8000" cmd /k "%PYTHON% orchestrator.py"
timeout /t 5 /nobreak >nul

echo.
echo ============================================================
echo   All services are starting...
echo   Please wait 10 seconds for initialization
echo ============================================================
echo.
timeout /t 10 /nobreak >nul

echo Checking service health...
curl -s http://localhost:8000/health

echo.
echo ============================================================
echo   READY TO USE!
echo ============================================================
echo.
echo   Service URLs:
echo   - Main API:     http://localhost:8000
echo   - API Docs:     http://localhost:8000/docs
echo   - Health Check: http://localhost:8000/health
echo.
echo   To use:
echo   1. Open index_updated.html in your browser
echo   2. Enter your story and click Generate
echo.
echo   To stop all services:
echo   - Close all command windows, or
echo   - Run: taskkill /F /FI "WINDOWTITLE eq *Generator*"
echo.
echo ============================================================

pause