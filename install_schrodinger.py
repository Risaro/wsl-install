#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

# --- Глобальные переменные ---
LOG_FILE = None

def log(message):
    """Записывает сообщение в консоль и в лог-файл"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    if LOG_FILE:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")

def run(cmd, sudo=False, check=False, shell=False, env=None):
    """Универсальный запуск команды"""
    if sudo:
        if isinstance(cmd, str):
            full_cmd = f"sudo {cmd}"
        elif isinstance(cmd, list):
            full_cmd = ["sudo"] + cmd
        else:
            raise TypeError("cmd must be str or list")
    else:
        full_cmd = cmd

    try:
        result = subprocess.run(
            full_cmd,
            shell=shell,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            env=env or os.environ
        )
        return result
    except Exception as e:
        log(f"❌ Ошибка выполнения: {full_cmd}")
        log(f"   {e}")
        sys.exit(1)

def install_x11_deps():
    """Установка X11/Qt-зависимостей"""
    log("🔧 Устанавливаем зависимости для GUI (X11, Qt, xcb)...")
    packages = [
        "libxcb-cursor0", "libxkbcommon-x11-0", "libxcb-xinerama0",
        "libxcb-randr0", "libxcb-xtest0", "libxcb-shape0", "libxcb-xfixes0",
        "libx11-xcb1", "libxcb1",
        "libxcb-util1", "libxcb-icccm4", "libxcb-keysyms1", "libxcb-image0",
        "libxcb-render-util0", "libxrender1", "libxext6", "libx11-6",
        "libglx-mesa0", "libdbus-1-3", "xorg"
    ]

    failed = []
    for pkg in packages:
        result = run(["apt", "install", "-y", pkg], sudo=True, check=False)
        if result.returncode != 0:
            log(f"❌ Не удалось установить {pkg}")
            failed.append(pkg)
        else:
            log(f"✅ {pkg} установлен")

    if failed:
        log(f"⚠️  Не установлены пакеты: {', '.join(failed)}")
        log("💡 Попробуйте установить их вручную.")
    else:
        log("✅ Все зависимости установлены")

def create_windows_shortcut(schrod_dir, wsl_user):
    """
    Создаёт .bat-файл-ярлык для запуска Maestro на Windows
    """
    log("📌 Создаём ярлык для Maestro на Windows...")
    script_dir = Path.cwd()
    shortcut_path = script_dir / "Запустить Maestro.bat"

   

    # Команда для .bat файла
    bat_content = f'''@echo off
    chcp 65001 >nul
echo Запускаем Maestro...
wsl -d Ubuntu -u {wsl_user} -e bash -c "export SCHRODINGER={schrod_dir}; $SCHRODINGER/maestro"
if %errorlevel% neq 0 (
    echo.
    echo ОШИБКА: Не удалось запустить Maestro.
    echo Убедитесь, что WSL запущен и Schrödinger установлен.
    pause
)
'''

    try:
        shortcut_path.write_text(bat_content, encoding='utf-8')
        log(f"✅ Ярлык создан: {shortcut_path}")
        log("💡 Переместите его на рабочий стол или в меню Пуск")
    except Exception as e:
        log(f"❌ Не удалось создать ярлык: {e}")

def main():
    global LOG_FILE

    print("🚀 Установка Schrödinger Suite 2025-2")
    print("=" * 60)

    # --- 1. Определяем текущую директорию
    current_dir = Path.cwd()
    log(f"📁 Рабочая папка: {current_dir}")

    # --- 2. Путь к дистрибутиву
    distro_dir = current_dir / "Schrodinger_Suites_2025-2_Linux-x86_64"
    install_script = distro_dir / "INSTALL"
    if not install_script.exists():
        log(f"🛑 Не найден файл установки: {install_script}")
        log("💡 Убедитесь, что вы запускаете скрипт из папки с дистрибутивом.")
        sys.exit(1)

    # --- 3. Спрашиваем пути
    schrod_dir_input = input("Введите путь установки Schrödinger [/opt/schrodinger]: ").strip()
    schrod_dir = Path(schrod_dir_input or "/opt/schrodinger").resolve()
    log(f"Путь установки: {schrod_dir}")

    thirdparty_dir_input = input(f"Введите путь для thirdparty [{schrod_dir}/thirdparty]: ").strip()
    thirdparty_dir = Path(thirdparty_dir_input or f"{schrod_dir}/thirdparty").resolve()

    tmp_dir_input = input(f"Введите путь для временных файлов [/tmp/schrodinger]: ").strip()
    tmp_dir = Path(tmp_dir_input or "/tmp/schrodinger").resolve()

    log(f"Путь thirdparty: {thirdparty_dir}")
    log(f"Временная папка: {tmp_dir}")

    # --- 4. Создаём директории
    log("🔧 Создаём директории...")
    try:
        schrod_dir.mkdir(parents=True, exist_ok=True)
        thirdparty_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        log(f"🛑 Нет прав на создание директории: {schrod_dir}")
        log("💡 Запустите скрипт с sudo: sudo python3 install_schrodinger.py")
        sys.exit(1)

    # --- 5. Настройка логирования
    logs_dir = schrod_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = logs_dir / f"install_{timestamp}.log"
    log(f"📄 Лог установки сохраняется в: {LOG_FILE}")

    # --- 6. Список всех модулей (точно как в твоей команде)
    all_files = [
        "bioluminate-v5.9-Linux-x86_64.tar.gz",
        "canvas-v6.4-Linux-x86_64.tar.gz",
        "combiglide-v7.7-Linux-x86_64.tar.gz",
        "desmond-v8.2-Linux-x86_64.tar.gz",
        "docs_data-v7.0-docs.tar.gz",
        "epik-v7.2-Linux-x86_64.tar.gz",
        "glide-v10.7-Linux-x86_64.tar.gz",
        "impact-v10.7-Linux-x86_64.tar.gz",
        "jaguar-v12.8-Linux-x86_64.tar.gz",
        "knime-v7.0-Linux-x86_64.tar.gz",
        "macromodel-v14.8-Linux-x86_64.tar.gz",
        "maestro-v14.4-Linux-x86_64.tar.gz",
        "mmshare-v7.0-Linux-x86_64.tar.gz",
        "psp-v8.0-Linux-x86_64.tar.gz",
        "psp-homology-thirdparty-databases.tar.gz",
        "qikprop-v8.4-Linux-x86_64.tar.gz",
        "watermap-v6.3-Linux-x86_64.tar.gz"
    ]

    # Проверка наличия всех файлов
    missing = [f for f in all_files if not (distro_dir / f).exists()]
    if missing:
        log(f"🛑 Не найдены следующие файлы:")
        for f in missing:
            log(f"   - {f}")
        sys.exit(1)
    log(f"✅ Все 17 файлов найдены")

    # --- 7. Устанавливаем зависимости для GUI
    install_x11_deps()

    # --- 8. Подготавливаем переменные окружения
    env = os.environ.copy()
    env["AUTO_MMSHARE"] = "y"
    env["AUTO_DOCS"] = "y"
    env["AUTO_DATA"] = "y"
    env["AUTO_PATCH"] = "y"

    # --- 9. Команда установки (как в твоём примере)
    cmd = [
        "bash", str(install_script),
        "-b",
        "-s", str(schrod_dir),
        "-d", str(distro_dir),
        "-t", str(thirdparty_dir),
        "-k", str(tmp_dir)
    ] + all_files

    # --- 10. Запускаем установку
    log("🔄 Начало установки Schrödinger...")
    result = subprocess.run(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        cwd=str(distro_dir)
    )

    for line in result.stdout.splitlines():
        log(f"INSTALL | {line}")

    if result.returncode != 0:
        log("❌ Установка завершилась с ошибкой")
        sys.exit(1)
    else:
        log("✅ Установка Schrödinger завершена успешно")

       # --- 11. Копируем libmmfileshared.so ---
    source_so = current_dir / "internal" / "lib" / "libmmfileshared.so"
    target_lib = schrod_dir / "internal" / "lib"
    target_so = target_lib / "libmmfileshared.so"

    if source_so.exists():
        log(f"🔁 Копируем {source_so.name} в {target_so}...")
        target_lib.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_so, target_so)
        log("✅ libmmfileshared.so скопирован")
    else:
        log("⚠️  Файл libmmfileshared.so не найден в исходной папке internal")

    # --- 12. Копируем licenses (если нужно) ---
    source_licenses = current_dir / "licenses"
    target_licenses = schrod_dir / "licenses"

    if source_licenses.exists():
        log(f"🔁 Копируем licenses в {target_licenses}...")
        if target_licenses.exists():
            shutil.rmtree(target_licenses)
        shutil.copytree(source_licenses, target_licenses)
        log("✅ Папка licenses скопирована")

    # --- 12. Спрашиваем имя пользователя WSL
    wsl_user = input("Введите имя пользователя WSL (для ярлыка): ").strip()
    if not wsl_user:
        log("⚠️ Имя пользователя не введено, ярлык не будет создан.")
    else:
        create_windows_shortcut(schrod_dir, wsl_user)

    # --- 13. Финал
    log("=" * 50)
    log("✅ УСТАНОВКА ЗАВЕРШЕНА!")
    log(f"🖥️  Schrödinger установлен в: {schrod_dir}")
    log(f"📄 Лог: {LOG_FILE}")
    log(f"💡 Добавьте в ~/.bashrc: export SCHRODINGER={schrod_dir}")
    log(f"💡 Запустите: \$SCHRODINGER/utilities/configure для лицензии")

    choice = input("Запустить utilities/configure? [y/N]: ").strip().lower()
    if choice in ['y', 'yes']:
        configure_path = schrod_dir / "utilities" / "configure"
        if configure_path.exists():
            log("🔧 Запускаем Schrödinger Configuration Tool...")
            run([str(configure_path)], shell=True)
        else:
            log(f"⚠️ Файл {configure_path} не найден")

if __name__ == "__main__":
    main()

