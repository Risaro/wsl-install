#!/usr/bin/env python3

import os
import sys
import subprocess
import getpass
from pathlib import Path

def run(cmd, sudo=True, check=True, shell=False):
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
            return e
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неизвестная ошибка: {e}")
        sys.exit(1)

def detect_gpu():
    """Определяем тип GPU"""
    print("🔍 Определяем тип GPU...")
    result = run(["lspci", "-v"], check=False)
    if result.returncode != 0:
        print("⚠️ Не удалось выполнить lspci. Устанавливаем CPU OpenCL...")
        return "unknown"
    output = result.stdout.lower()
    if "nvidia" in output:
        return "nvidia"
    elif "amd" in output or "radeon" in output:
        return "amd"
    elif "intel" in output:
        return "intel"
    else:
        return "unknown"

def fix_wsl_conf(username):
    """Настройка /etc/wsl.conf с автозапуском dbus и xrdp"""
    print("⚙️ Настраиваем /etc/wsl.conf...")
    wsl_conf = f'''[automount]
enabled=true

[user]
default={username}

[boot]
command = "sudo service dbus start; sudo service xrdp start"
'''
    conf_path = "/tmp/wsl.conf"
    Path(conf_path).write_text(wsl_conf, encoding='utf-8')
    run(["cp", conf_path, "/etc/wsl.conf"])
    print("✅ /etc/wsl.conf настроен (автозапуск dbus и xrdp)")

def fix_xrdp_config(username):
    """Исправляем startwm.sh для xRDP"""
    print("🔧 Исправляем /etc/xrdp/startwm.sh...")
    startwm_content = '''#!/bin/sh
        if [ -r /etc/X11/xinit/xinitrc ]; then
          . /etc/X11/xinit/xinitrc
        else
          startxfce4 &
        fi
        '''
    startwm_path = "/tmp/startwm.sh"
    Path(startwm_path).write_text(startwm_content, encoding='utf-8')
    run(["cp", startwm_path, "/etc/xrdp/startwm.sh"])
    run(["chmod", "+x", "/etc/xrdp/startwm.sh"])
    print("✅ /etc/xrdp/startwm.sh обновлён")
def setup_keyboard_layout(username, home_dir):
    """Настройка раскладки: русский/английский через Left Shift + Left Alt"""
    print("⌨️  Настраиваем переключение раскладки (рус/англ)...")

    # Путь к конфигу XFCE
    xfconf_dir = f"{home_dir}/.config/xfce4/xfconf/xfce-perchannel-xml"
    os.makedirs(xfconf_dir, exist_ok=True)
    keyboard_file = f"{xfconf_dir}/keyboard-layout.xml"

    # XML-конфиг для xfconf
    keyboard_xml = '''<?xml version="1.0" encoding="UTF-8"?>
            <channel name="keyboard-layout" version="1.0">
              <property name="Default" type="empty">
                <property name="XkbDisable" type="bool" value="false"/>
                <property name="XkbLayout" type="string" value="us,ru"/>
                <property name="XkbVariant" type="string" value=",winkeys"/>
                <property name="XkbOptions" type="string" value="grp:lalt_lshift_toggle,grp_led:scroll"/>
              </property>
            </channel>
            '''
    # Сохраняем файл
    Path(keyboard_file).write_text(keyboard_xml, encoding='utf-8')
    run(["chown", "-R", f"{username}:{username}", f"{home_dir}/.config"])

    # Добавляем в автозагрузку (на случай, если xfconf не примет XML)
    autostart_dir = f"{home_dir}/.config/autostart"
    os.makedirs(autostart_dir, exist_ok=True)
    kbd_desktop = f"{autostart_dir}/set-keyboard.desktop"

    autostart_entry = '''[Desktop Entry]
            Type=Application
            Name=Set Keyboard Layout
            Exec=setxkbmap -layout "us,ru" -variant ",winkeys" -option "grp:lalt_lshift_toggle,grp_led:scroll"
            Hidden=false
            NoDisplay=true
            X-GNOME-Autostart-enabled=true
            '''
    Path(kbd_desktop).write_text(autostart_entry, encoding='utf-8')
    run(["chmod", "+x", kbd_desktop])
    run(["chown", "-R", f"{username}:{username}", autostart_dir])

    print("✅ Раскладка настроена: Shift+Alt — переключение между us/ru")
def fix_user_session(username, home_dir):
    """Создаём .xsession и .xprofile"""
    print(f"📁 Настраиваем сессию для {username}...")

    # .xsession
    xsession = f"{home_dir}/.xsession"
    Path(xsession).write_text("startxfce4\n", encoding='utf-8')
    run(["chown", f"{username}:{username}", xsession])
    run(["chmod", "+x", xsession])

    # .xprofile — отключаем WSLg
    xprofile = f"{home_dir}/.xprofile"
    xprofile_content = '''unset DISPLAY
unset WAYLAND_DISPLAY
unset XDG_SESSION_TYPE
'''
    Path(xprofile).write_text(xprofile_content, encoding='utf-8')
    run(["chown", f"{username}:{username}", xprofile])

    print("✅ .xsession и .xprofile настроены")

def install_gui(username):
    """Установка XFCE и xRDP"""
    print("🎨 Устанавливаем XFCE и xRDP...")
    run(["apt", "update", "-qq"])
    run(["apt", "install", "-y", "xfce4", "xfce4-goodies", "xrdp", "dbus-x11", "xorg"])

    # Права для xrdp
    run(["adduser", "xrdp", "ssl-cert"])

    # fix_user_session и setup_keyboard_layout вызываются в main()
    # где home_dir уже определён

    # Включаем автозапуск xrdp
    run(["systemctl", "enable", "xrdp"], check=False)

    print("✅ GUI и xRDP установлены и настроены")

def install_tools():
    """Установка базовых инструментов"""
    print("🛠️ Устанавливаем htop, nano, git, curl...")
    run(["apt", "install", "-y",
         "htop", "nano", "wget", "curl", "git",
         "software-properties-common", "gnupg2", "net-tools","pciutils","python3"])
    print("✅ Инструменты установлены")

def install_nvidia():
    """Установка CUDA для WSL"""
    print("📦 Устанавливаем CUDA для NVIDIA...")
    run(["apt-key", "adv", "--fetch-keys", "https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/3bf863cc.pub"])
    run(["add-apt-repository", "deb https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/ /", "-y"])
    run(["apt", "update"])
    run(["apt", "install", "-y", "cuda-toolkit"])
    run(["nvidia-smi"])
    print("✅ CUDA установлен")

def install_amd():
    """Установка ROCm"""
    print("📦 Устанавливаем ROCm для AMD...")
    run(["apt", "install", "-y", "wget", "gnupg2"])
    result = run(["wget", "-q", "-O", "-", "https://repo.radeon.com/rocm/rocm.gpg.key"], stdout=subprocess.PIPE)
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

    # Проверка пользователя
    result = run(["id", "-u", username], check=False)
    if result.returncode != 0:
        print(f"🛑 Пользователь '{username}' не существует!")
        sys.exit(1)
    print(f"✅ Пользователь '{username}' существует (UID: {result.stdout.strip()})")

    # Выполняем настройку
    fix_wsl_conf(username)
    # --- Получаем домашнюю директорию пользователя ---
    result = run(["getent", "passwd", username], check=False)
    if result.returncode != 0:
        print(f"🛑 Не удалось получить информацию о пользователе '{username}'")
        sys.exit(1)
    # Парсим строку passwd: user:x:1000:1000:,,,:/home/user:/bin/bash
    home_dir = result.stdout.strip().split(':')[5]

    # Теперь можно вызывать функции, требующие home_dir
    fix_user_session(username, home_dir)
    setup_keyboard_layout(username, home_dir)
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
    print("   При подключении выберите 'Xorg' в поле 'Модуль подключения'")
    print("="*60)
    print("ОБЯЗАТЕЛЬНО ПЕРЕЗАПУСТИТЕ WSL , ЧТОБЫ НАСТРОЙКИ ПРИМЕНИЛИСЬ")
    print("откройте CMD")
    print("wsl --shutdown")
    print("wsl")
    print("Все и все настроенно")

if __name__ == "__main__":
    main()
