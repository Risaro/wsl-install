@echo off
chcp 65001 >nul
:: =================================================
:: WSL INSTALL LAUNCHER
:: Runs setup-wsl.ps1 with admin rights
:: =================================================

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [!] Administrator rights required.
    echo     Please run as Administrator.
    echo.
    pause
    exit /b
)

cd /d "%~dp0"

if not exist "setup-wsl.ps1" (
    echo.
    echo [!] setup-wsl.ps1 not found!
    echo     Place it in the same folder.
    echo.
    pause
    exit /b
)

echo [+] Launching WSL setup...
powershell -ExecutionPolicy Bypass -NoProfile -File "setup-wsl.ps1"

echo.
echo [+] Setup finished. Press any key to exit.
pause >nul