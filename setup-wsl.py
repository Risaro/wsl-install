#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import platform
import getpass
from pathlib import Path

def run(cmd, sudo=False, shell=False, check=True, env=None):
    """Универсальный запуск команды"""
    if sudo and not cmd.startswith("sudo "):
        cmd = f"sudo {cmd}"
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            env=env or os.environ
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения: {cmd}")
        print(f"   Код: {e.returncode}")
        print(f"   Ошибка: {e.stderr.strip()}")
        sys.exit(1)

def detect_gpu():
    """Определяем тип GPU (в WSL он доступен через dxdiag в Windows, но можно попробовать через lspci)"""
    print("🔍 Определяем тип GPU...")
    result = run("lspci -v", shell=True, check=False)
    if result.returncode != 0:
        print("⚠️ Не удалось выполнить lspci. Установка CPU OpenCL...")
        return "unknown"

    output = result.stdout.lower()
    if "nvidia" in output:
        return "nvidia"
    elif "amd" in output or "radeon" in output or "advanced micro devices" in output:
        return "amd"
    elif "intel" in output:
        return "intel"
    else:
        return "unknown"

def setup_wsl_conf(username):
    """Настройка /etc/wsl.conf"""
    print("⚙️ Настраиваем /etc/wsl.conf...")
    wsl_conf = '''[automount]
enabled=true

[user]
default={}

[boot]
command = "service dbus start"
'''.format(username)

    conf_path = "/tmp/wsl.conf"
    Path(conf_path).write_text(wsl_conf, encoding='utf-8')

    run(f"sudo cp {conf_path} /etc/wsl.conf")
    print("✅ /etc/wsl.conf настроен")

def install_gui(username):
    """Установка XFCE и xRDP"""
    print("🎨 Устанавливаем XFCE и xRDP...")
    run("sudo apt update -qq")
    run("sudo apt install -y xfce4 xfce4-goodies xrdp dbus-x11")

    # Настройка .xsession
    session_file = f"/home/{username}/.xsession"
    run(f"echo 'xfce4-session' | sudo tee {session_file}")
    run(f"sudo chown {username}:{username} {session_file}")

    # Запуск xRDP
    run("sudo service xrdp start")
    run("sudo systemctl enable xrdp", check=False)

    print("✅ GUI установлен")

def install_tools():
    """Установка базовых инструментов"""
    print("🛠️ Устанавливаем htop, nano, git, curl...")
    run("sudo apt install -y htop nano wget curl git software-properties-common")
    print("✅ Инструменты установлены")

def install_nvidia():
    """Установка CUDA для WSL"""
    print("📦 Устанавливаем CUDA для NVIDIA...")
    run("wget -q https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin")
    run("sudo mv cuda-wsl-ubuntu.pin /etc/apt/sources.list.d/cuda-pin.list")
    run("sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/3bf863cc.pub")
    run('sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/ /" -y')
    run("sudo apt update")
    run("sudo apt install -y cuda-toolkit-12-4")
    run("nvidia-smi")
    print("✅ CUDA установлен")

def install_amd():
    """Установка ROCm"""
    print("📦 Устанавливаем ROCm для AMD...")
    run("sudo apt install -y wget gnupg2")
    run("wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -")
    run('echo "deb [arch=amd64] https://repo.radeon.com/rocm/apt/5.7 jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list')
    run("sudo apt update")
    run("sudo apt install -y rocm-opencl-runtime rocm-utils")
    run(f"sudo usermod -aG render {getpass.getuser()}")
    print("✅ ROCm установлен")

def install_intel():
    """Установка драйверов Intel"""
    print("📦 Устанавливаем драйверы Intel...")
    run("sudo apt install -y intel-level-zero-gpu intel-opencl-icd")
    print("✅ Драйверы Intel установлены")

def install_cpu_opencl():
    """Установка OpenCL для CPU"""
    print("📦 Устанавливаем OpenCL для CPU...")
    run("sudo apt install -y ocl-icd-opencl-dev pocl-opencl-icd")
    print("✅ CPU OpenCL установлен")

def main():
    if os.geteuid() != 0:
        print("⚠️ Скрипт должен запускаться от root (через sudo)")
        sys.exit(1)

    # Получаем имя пользователя (передаётся из PowerShell)
    if len(sys.argv) < 2:
        print("❌ Использование: sudo python3 setup-wsl.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    print(f"🔐 Настройка для пользователя: {username}")

    # Проверим, существует ли пользователь
    result = run(f"id -u {username}", check=False)
    if result.returncode != 0:
        print(f"🛑 Пользователь '{username}' не существует!")
        sys.exit(1)

    # Выполняем шаги
    setup_wsl_conf(username)
    install_gui(username)
    install_tools()

    gpu = detect_gpu()
    print(f"🎮 GPU: {gpu.upper()}")

    if gpu == "nvidia":
        install_nvidia()
    elif gpu == "amd":
        install_amd()
    elif gpu == "intel":
        install_intel()
    else:
        install_cpu_opencl()

    # Финал
    ip = run("hostname -I | awk '{print $1}'", shell=True).stdout.strip()
    print("\n" + "="*50)
    print("✅ УСТАНОВКА ЗАВЕРШЕНА!")
    print(f"🖥️  Пользователь: {username}")
    print(f"🌐 IP-адрес: {ip}")
    print(f"💡 Подключайтесь по RDP к {ip}:3389")
    print("   Логин: имя пользователя и пароль от WSL")
    print("="*50)

if __name__ == "__main__":
    main()
