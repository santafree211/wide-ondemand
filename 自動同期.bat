@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo === WIDE-ONDEMAND AUTO-SYNCHRONIZER ===
echo ==========================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\wide\sync_wide_pipeline.ps1"

echo.
echo ==========================================================
echo Press any key to close this console window...
echo ==========================================================
pause >nul
