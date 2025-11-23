@echo off
REM ============================================================
REM   AI Comic Book Generator - Stop All Services
REM ============================================================

echo.
echo ============================================================
echo   Stopping All Services...
echo ============================================================
echo.

REM Kill all Python processes running the generators
taskkill /F /FI "WINDOWTITLE eq Scene Generator*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Image Generator*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Bubble Placement*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Dialogue Generator*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Bubble Renderer*" 2>nul
taskkill /F /FI "WINDOWTITLE eq Main Orchestrator*" 2>nul

echo.
echo   All services stopped!
echo.

pause