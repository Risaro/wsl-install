# encoding: utf-8
# =============================================
# УСТАНОВКА WSL С GUI, GPU, ПАРОЛЯМИ И АВТОВОЗОБНОВЛЕНИЕМ
# С РУЧНЫМ ВВОДОМ ПОЛЬЗОВАТЕЛЯ ПОСЛЕ ИНИЦИАЛИЗАЦИИ
# =============================================
# ---------------------------------------------------
# 0. ГАРАНТИРУЕМ ДОСТУП К СИСТЕМНЫМ КОМАНДАМ
# ---------------------------------------------------
$system32 = "C:\Windows\System32"
Write-Host "🔧 Провека , что присутвует  $system32 в PATH..." -ForegroundColor Yellow
if ($env:PATH -notlike "*$system32*") {
    Write-Host "🔧 Добавляем $system32 в PATH..." -ForegroundColor Yellow
    $env:PATH = "$system32;$env:PATH"
}
$setupStageKey = "HKCU:\Software\WSL-Setup"
$setupStageValue = "CurrentStage"
$distroName = $null
$wslUser = $null
$defaultPassword = $null

# Устанавливаем кодировку для кириллицы
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Функция: записать текущий этап
function Set-SetupStage($stage) {
    if (-not (Test-Path $setupStageKey)) {
        New-Item -Path $setupStageKey -Force | Out-Null
    }
    Set-ItemProperty -Path $setupStageKey -Name $setupStageValue -Value $stage
}

# Функция: получить текущий этап
function Get-SetupStage {
    if (Test-Path $setupStageKey) {
        return (Get-ItemProperty -Path $setupStageKey -Name $setupStageValue -ErrorAction SilentlyContinue).$setupStageValue
    }
    return "start"
}

# Функция: очистить этап (по завершении)
function Clear-SetupStage {
    if (Test-Path $setupStageKey) {
        Remove-Item -Path $setupStageKey -Recurse -Force
    }
}

Clear-SetupStage
# Получаем текущий этап
$stage = Get-SetupStage
Write-Host "🔄 Этап установки: $stage" -ForegroundColor Cyan
Write-Host ""

# Восстанавливаем имя дистрибутива из реестра
if (Test-Path $setupStageKey) {
    $savedDistro = (Get-ItemProperty -Path $setupStageKey -Name "DistroName" -ErrorAction SilentlyContinue).DistroName
    if ($savedDistro -and (wsl --list --quiet | Where-Object { $_ -eq $savedDistro })) {
        $distroName = $savedDistro
        Write-Host "🔁 Восстановлено имя дистрибутива: $distroName" -ForegroundColor Green
    }
}

# ---------------------------------------------------
# 1. УМНАЯ ПРОВЕРКА ВИРТУАЛИЗАЦИИ
# ---------------------------------------------------
if ($stage -eq "start" -or $stage -eq "reboot-pending") {
    Write-Host "🔍 Проверка виртуализации..." -ForegroundColor Cyan
    $hypervisor = (Get-WmiObject -Class Win32_ComputerSystem).HypervisorPresent
    $vmFirmware = (Get-ComputerInfo).VirtualizationFirmwareEnabled

    if ($hypervisor -eq $true) {
        Write-Host "✅ Гипервизор обнаружен. Виртуализация работает." -ForegroundColor Green
    } elseif ($vmFirmware -eq $true) {
        Write-Host "✅ Виртуализация включена в BIOS." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "🛑 Виртуализация, возможно, отключена в BIOS." -ForegroundColor Red
        Write-Host ""
        Write-Host "💡 Включите в BIOS:"
        Write-Host "   • Intel: Intel VT-x"
        Write-Host "   • AMD: SVM Mode"
        Write-Host "   • Сохраните: F10"
        Write-Host ""
        Write-Host "   Или отключите конфликтующие программы: Hyper-V, антивирусы."
        Write-Host ""
        Read-Host "Нажмите Enter для продолжения"
    }
}

# ---------------------------------------------------
# 2. ВКЛЮЧАЕМ КОМПОНЕНТЫ WSL (требует перезагрузки)
# ---------------------------------------------------
if ($stage -eq "start" -or $stage -eq "reboot-pending") {
    Write-Host "🔧 Включаем компоненты WSL..." -ForegroundColor Cyan
    $wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -ErrorAction SilentlyContinue
    $vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -ErrorAction SilentlyContinue

    $restartNeeded = $false
    if ($wslFeature.State -ne "Enabled") {
        Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux -NoRestart
        $restartNeeded = $true
    }
    if ($vmFeature.State -ne "Enabled") {
        Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -NoRestart
        $restartNeeded = $true
    }

    if ($restartNeeded) {
        Write-Host "🔄 Требуется перезагрузка. Перезагружаем через 10 секунд..." -ForegroundColor Yellow
        Set-SetupStage "reboot-pending"

        $currentScript = (Get-Item $PSCommandPath).FullName
        $trigger = New-JobTrigger -AtStartup
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$currentScript`""
        Register-ScheduledTask -TaskName "ContinueWSLSetup" -Trigger $trigger -Action $action -User "NT AUTHORITY\SYSTEM" -RunLevel Highest -Force

        Start-Sleep -Seconds 10
        Restart-Computer -Force
        exit
    }

    Set-SetupStage "wsl-components-enabled"
    $stage = "wsl-components-enabled"
}

# ---------------------------------------------------
# 3. УСТАНАВЛИВАЕМ WSL2 КАК ВЕРСИЮ ПО УМОЛЧАНИЮ
# ---------------------------------------------------
if ($stage -eq "wsl-components-enabled") {
    Write-Host "🔧 Устанавливаем WSL 2 как версию по умолчанию..." -ForegroundColor Cyan
    wsl --set-default-version 2 | Out-Null
    Set-SetupStage "wsl-default-version-set"
    $stage = "wsl-default-version-set"
}

# ---------------------------------------------------
# 4. ОПРЕДЕЛЕНИЕ ДИСТРИБУТИВА
# ---------------------------------------------------
if ($stage -eq "wsl-default-version-set") {
    Write-Host "📦 Поиск установленного Ubuntu-дистрибутива..." -ForegroundColor Cyan

    $installedDistros = wsl --list --quiet 2>$null | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
    $ubuntuDistros = $installedDistros | Where-Object { "Ubuntu" }

    if ($ubuntuDistros) {
        $distroName = $ubuntuDistros | Select-Object -First 1
        Write-Host "✅ Найден дистрибутив: $distroName" -ForegroundColor Green
        wsl --set-default $distroName
    } else {
        Write-Host "🛠️  Ubuntu не найден. Устанавливаем по умолчанию..." -ForegroundColor Yellow
        wsl --install --no-launch
        Start-Sleep -Seconds 15

        $installedDistros = wsl --list --quiet 2>$null | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" }
        $ubuntuDistros = $installedDistros | Where-Object { $_ -match "Ubuntu" }

        if ($ubuntuDistros) {
            $distroName = $ubuntuDistros | Select-Object -First 1
            Write-Host "✅ Установлен и найден: $distroName" -ForegroundColor Green
            wsl --set-default $distroName
        } else {
            Write-Host "🛑 Не удалось установить Ubuntu." -ForegroundColor Red
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Write-Host "Ничего страшного , скорее всего у вас октрылся popup WSL такое бывает , перезапустите скрипт установки." -ForegroundColor Green
            Read-Host "Нажмите Enter для завершения"
            exit 1
        }
    }

    # Сохраняем имя дистрибутива
    Set-ItemProperty -Path $setupStageKey -Name "DistroName" -Value $distroName
    Set-SetupStage "distro-installed"
    $stage = "distro-installed"
}

# ---------------------------------------------------
# 5. ПРОВЕРКА И УСТАНОВКА WINGET
# ---------------------------------------------------
if ($stage -eq "distro-installed") {
    Write-Host "🔍 Проверка winget..." -ForegroundColor Cyan
    if (!(Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "⚠️  Устанавливаем winget..." -ForegroundColor Yellow
        $tempDir = "$env:TEMP\wsl-setup"
        $msix = "$tempDir\appinstaller.msixbundle"
        $cert = "$tempDir\cert.cer"
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        Remove-Item $msix, $cert -ErrorAction SilentlyContinue

        try {
            Invoke-WebRequest -Uri "https://github.com/microsoft/winget-cli/releases/latest/download/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle" -OutFile $msix
            Invoke-WebRequest -Uri "https://github.com/microsoft/winget-cli/releases/latest/download/Microsoft.Winget.Installer.Certificate.cer" -OutFile $cert
            certutil -addstore "TrustedPeople" $cert | Out-Null
            Add-AppxPackage -Path $msix
            Write-Host "✅ winget установлен!" -ForegroundColor Green
        } catch {
            Write-Host "🛑 Ошибка установки winget. Продолжаем..." -ForegroundColor Red
        }
    }
}

# ---------------------------------------------------
# 6. РУЧНОЙ ВВОД ПОЛЬЗОВАТЕЛЯ И ПРОВЕРКА (УЛУЧШЕННЫЙ ВАРИАНТ)
# ---------------------------------------------------
if ($stage -eq "distro-installed") {
    if (-not $distroName) {
        Write-Host "🛑 Ошибка: имя дистрибутива не определено!" -ForegroundColor Red
        Read-Host "Нажмите Enter"
        exit 1
    }

    Write-Host ""
    Write-Host "📌 ВАЖНО: Перед продолжением:" -ForegroundColor Yellow
    Write-Host "   1. Откройте новое окно PowerShell"
    Write-Host "   2. Выполните: wsl"
    Write-Host "   3. Создайте пользователя и пароль при запросе"
    Write-Host "   4. После завершения настройки не закрывайте ОКНО ОЧЕНЬ ВАЖНО !!! ОБХОД ПОЛИТИКИ WINDOWS :(" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Пример:"
    Write-Host "     New UNIX username: user"
    Write-Host "     New UNIX password: gtadmin123!"
    Write-Host ""
    Write-Host "✅ После этого вернитесь сюда и нажмите Enter"
    Write-Host ""
    Read-Host "Нажмите Enter, когда WSL инициализирован"

    Write-Host ""
    $wslUser = Read-Host "Введите имя пользователя, которое вы создали в WSL"
    $defaultPassword = Read-Host "Введите пароль, который вы задали"

    Write-Host ""
    Write-Host "🔍 Проверяем, существует ли пользователь '$wslUser' в WSL..." -ForegroundColor Cyan

    # === КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: ПРОСТО ВЫПОЛНЯЕМ КОМАНДУ НАПРЯМУЮ ===
    $result = wsl -d Ubuntu -e bash -c "id -u '$wslUser' 2>/dev/null || echo 'not_found'" 2>$null

    if ($result -eq "not_found") {
        Write-Host "🛑 Пользователь '$wslUser' не существует." -ForegroundColor Red
        Write-Host "💡 Убедитесь, что вы правильно ввели имя и создали его в WSL."
        Read-Host "Нажмите Enter для завершения"
        exit 1
    }
    elseif ($result -match "^\d+$") {
        Write-Host "✅ Пользователь '$wslUser' существует (UID: $result)." -ForegroundColor Green

        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        Write-Host "Перезапустите скрипт установки install.bat от имени Администратора! Для настройки самой системы" -ForegroundColor Cyan
        # Сохраняем для следующего этапа
        Set-ItemProperty -Path $setupStageKey -Name "WslUser" -Value $wslUser
        Set-ItemProperty -Path $setupStageKey -Name "WslPassword" -Value $defaultPassword
        Set-SetupStage "user-validated"
    }
    else {
        Write-Host "⚠️ Неожиданный ответ: '$result'" -ForegroundColor Yellow
        Read-Host "Нажмите Enter для завершения"
        exit 1
    }
}

# ---------------------------------------------------
# 7. ЗАПУСК ВНЕШНЕГО PYTHON-СКРИПТА ВНУТРИ WSL
# ---------------------------------------------------
if ($stage -eq "user-validated") {
    $wslUser = (Get-ItemProperty -Path $setupStageKey -Name "WslUser" -ErrorAction SilentlyContinue).WslUser
    if (-not $wslUser) {
        Write-Host "🛑 Не удалось получить имя пользователя." -ForegroundColor Red
        exit 1
    }

    Write-Host "🚀 Загружаем и запускаем Python-скрипт внутри WSL..." -ForegroundColor Cyan

    $pythonScriptUrl = "https://raw.githubusercontent.com/Risaro/wsl-install/refs/heads/main/setup-wsl.py"
    $remoteScript = "/tmp/setup-wsl.py"

    # Установка Python, если нет
    $pythonCheck = wsl -d Ubuntu -e bash -c "command -v python3"
    if (-not $pythonCheck) {
        Write-Host "📦 Устанавливаем Python3..." -ForegroundColor Yellow
        wsl -d Ubuntu -u root -e apt install -y python3
    }

    # Скачиваем скрипт
    $downloadCmd = "wget -qO '$remoteScript' '$pythonScriptUrl'"
    wsl -d Ubuntu -u root -e bash -c $downloadCmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "🛑 Ошибка загрузки скрипта." -ForegroundColor Red
        exit 1
    }

    # Запускаем с передачей имени пользователя
    Write-Host "⚙️ Выполняем: python3 $remoteScript $wslUser"
    wsl -d Ubuntu -u root -e python3 $remoteScript $wslUser

    # Финал
    $ip = (wsl -d Ubuntu hostname -I).Trim()
    Write-Host ""
    Write-Host "🎉 Готово! Подключайтесь по RDP к $ip:3389" -ForegroundColor Green
    Unregister-ScheduledTask -TaskName "ContinueWSLSetup" -Confirm:$false -ErrorAction SilentlyContinue
    Clear-SetupStage
    Read-Host "Нажмите Enter для завершения"
}