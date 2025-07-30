#!/usr/bin/env python3

import os
import sys
import subprocess
import re
import getpass
from pathlib import Path

def run(cmd, sudo=True, check=True):
    """
    Выполняет команду через subprocess.run.
    :param cmd: список или строка команды
    :param sudo: добавить sudo
    :param check: вызывать исключение при ошибке
    :return: результат выполнения
    """
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
            shell=isinstance(full_cmd, str),
            check=check,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            env=os.environ
        )
        return result
    except FileNotFoundError as e:
        print(f"❌ Команда не найдена: {full_cmd}")
        print(f"   Ошибка: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения: {full_cmd}")
        print(f"   Код: {e.returncode}")
        if e.stderr:
            print(f"   Ошибка: {e.stderr.strip()}")
        if not check:
            return e  # Вернуть объект для обработки
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        sys.exit(1)

def detect_gpu():
    """Определяем тип GPU через lspci"""
    print("🔍 Определяем тип GPU...")
    result = run(["lspci", "-v"], check=False)
    if result.returncode != 0:
        print("⚠️ Не удалось выполнить lspci. Устанавливаем CPU OpenCL...")
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
    wsl_conf = f'''[automount]
enabled=true

[user]
default={username}

[boot]
command = "service dbus start"
'''
    conf_path = "/tmp/wsl.conf"
    Path(conf_path).write_text(wsl_conf, encoding='utf-8')
    run(["cp", conf_path, "/etc/wsl.conf"])
    print("✅ /etc/wsl.conf настроен")

def install_gui(username):
    """Установка XFCE и xRDP"""
    print("🎨 Устанавливаем XFCE и xRDP...")
    run(["apt", "update", "-qq"])
    run(["apt", "install", "-y", "xfce4", "xfce4-goodies", "xrdp", "dbus-x11"])

    # Настройка .xsession
    session_file = f"/home/{username}/.xsession"
    run(["sh", "-c", f"echo 'xfce4-session' > {session_file}"])
    run(["chown", f"{username}:{username}", session_file])

    # Запуск xRDP
    run(["service", "xrdp", "start"])
    run(["systemctl", "enable", "xrdp"], check=False)
    print("✅ GUI установлен")

def install_tools():
    """Установка базовых инструментов"""
    print("🛠️ Устанавливаем htop, nano, git, curl...")
    run(["apt", "install", "-y",
         "htop", "nano", "wget", "curl", "git",
         "software-properties-common", "gnupg2"])
    print("✅ Инструменты установлены")

def install_nvidia():
    """Установка CUDA для WSL"""
    print("📦 Устанавливаем CUDA для NVIDIA...")
    run(["wget", "-q", "https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-wsl-ubuntu.pin"])
    run(["mv", "cuda-wsl-ubuntu.pin", "/etc/apt/sources.list.d/cuda-pin.list"])
    run(["apt-key", "adv", "--fetch-keys", "https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/3bf863cc.pub"])
    run(["add-apt-repository", "deb https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/ /", "-y"])
    run(["apt", "update"])
    run(["apt", "install", "-y", "cuda-toolkit-12-4"])
    run(["nvidia-smi"])
    print("✅ CUDA установлен")

def install_amd():
    """Установка ROCm"""
    print("📦 Устанавливаем ROCm для AMD...")
    run(["apt", "install", "-y", "wget", "gnupg2"])
    run(["wget", "-q", "-O", "-", "https://repo.radeon.com/rocm/rocm.gpg.key"], stdout=subprocess.PIPE)
    result = subprocess.run(
        ["wget", "-q", "-O", "-", "https://repo.radeon.com/rocm/rocm.gpg.key"],
        capture_output=True, text=True
    )
    run(["apt-key", "add", "-"], input=result.stdout)
    run(["sh", "-c", "echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/5.7 jammy main' > /etc/apt/sources.list.d/rocm.list"])
    run(["apt", "update"])
    run(["apt", "install", "-y", "rocm-opencl-runtime", "rocm-utils"])
    run(["usermod", "-aG", "render", getpass.getuser()])
    print("✅ ROCm установлен")

def install_intel():
    """Установка драйверов Intel"""
    print("📦 Устанавливаем драйверы Intel...")
    run(["apt", "install", "-y", "intel-level-zero-gpu", "intel-opencl-icd"])
    print("✅ Драйверы Intel установлены")

def install_cpu_opencl():
    """Установка OpenCL для CPU"""
    print("📦 Устанавливаем OpenCL для CPU...")
    run(["apt", "install", "-y", "ocl-icd-opencl-dev", "pocl-opencl-icd"])
    print("✅ CPU OpenCL установлен")

def main():
    if os.geteuid() != 0:
        print("⚠️ Этот скрипт должен запускаться с правами root (через sudo).")
        print("   Пример: sudo python3 setup-wsl.py <username>")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("❌ Использование: sudo python3 setup-wsl.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    print(f"🔐 Настройка WSL для пользователя: {username}")

    # Проверка существования пользователя
    result = run(["id", "-u", username], check=False)
    if result.returncode != 0:
        print(f"🛑 Пользователь '{username}' не существует!")
        sys.exit(1)
    print(f"✅ Пользователь '{username}' существует (UID: {result.stdout.strip()})")

    # Выполнение настройки
    setup_wsl_conf(username)
    install_gui(username)
    install_tools()

    gpu = detect_gpu()
    print(f"🎮 Обнаружен GPU: {gpu.upper()}")

    if gpu == "nvidia":
        install_nvidia()
    elif gpu == "amd":
        install_amd()
    elif gpu == "intel":
        install_intel()
    else:
        install_cpu_opencl()

    # Финал
    ip = run(["hostname", "-I"], check=False).stdout.strip().split()[0]
    print("\n" + "="*60)
    print("✅ УСТАНОВКА WSL ЗАВЕРШЕНА!")
    print(f"🖥️  Пользователь: {username}")
    print(f"🌐 IP-адрес: {ip}")
    print(f"🚪 Порт RDP: 3389")
    print("💡 Подключайтесь через Remote Desktop к:")
    print(f"   {ip}:3389")
    print("   Логин: имя и пароль от WSL")
    print("="*60)

if __name__ == "__main__":
    main()
