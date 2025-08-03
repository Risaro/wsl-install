@echo off
chcp 65001 >nul
:: =============================================
:: ЗАПУСКАТОР WSL УСТАНОВКИ
:: Просто запускает PowerShell-скрипт от имени администратора
:: =============================================
 


:: Проверка на администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo 🛑 Требуются права Администратора!
    echo    Щёлкните правой кнопкой → "Запуск от имени администратора"
    echo.
    pause
    exit /b
)

:: Переходим в папку со скриптом
cd /d "%~dp0"

:: Проверяем, существует ли setup-wsl.ps1
if not exist "setup-wsl.ps1" (
    echo.
    echo 🛠️  Файл setup-wsl.ps1 не найден в этой папке!
    echo    Убедитесь, что он находится рядом с launch.bat
    echo.
    pause
    exit /b
)

:: Запускаем PowerShell-скрипт
echo 🚀 Запуск setup-wsl.ps1...
%SYSTEMROOT%\System32\WindowsPowerShell\v1.0\powershell.exe  -ExecutionPolicy Bypass -NoProfile -File "setup-wsl.ps1"

echo.
echo 🎉 Установка завершена. Нажмите любую клавишу...
pause >nul