# -*- coding: utf-8 -*-
"""
utils.py — общие утилиты: проверка бинарников, конвертация времени, шаблоны имен, открытие папки.
"""
import os
import subprocess
import sys

def which(name):
    """Ищем программу в PATH, возвращаем полный путь или None."""
    from shutil import which as _which
    return _which(name)

def check_bin(bin_path, *args):
    """Пробуем запустить бинарник с аргументами, возвращаем True/False."""
    try:
        subprocess.run([bin_path] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except Exception:
        return False

def open_folder(path):
    """Открыть папку средствами ОС (Windows/macOS/Linux)."""
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path])
    else:
        subprocess.run(["xdg-open", path])

def sec_to_hhmmss(sec):
    """Преобразовать секунды (float) в строку HH:MM:SS."""
    sec = int(round(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def sec_to_mmss(sec):
    """Преобразовать секунды (float) в строку MM:SS (часа не показываем)."""
    sec = int(round(sec))
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{m:02d}:{s:02d}"

def hhmmss_to_sec(text):
    """Преобразовать текст 'MM:SS' или 'HH:MM:SS' в секунды (float)."""
    parts = text.strip().split(":")
    parts = [p for p in parts if p != ""]
    if not parts:
        return 0.0
    parts = [int(p) for p in parts]
    if len(parts) == 2:
        m, s = parts
        return float(m*60 + s)
    if len(parts) == 3:
        h, m, s = parts
        return float(h*3600 + m*60 + s)
    # если формат неизвестен, вернуть 0
    return 0.0

def safe_out_path(out_dir, base_name, ext):
    """Версионирование файла, если такой уже существует: name.mp4 -> name(1).mp4 и т.д."""
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, base_name + "." + ext.lstrip("."))
    if not os.path.exists(path):
        return path
    i = 1
    while True:
        p = os.path.join(out_dir, f"{base_name}({i}).{ext.lstrip('.')}")
        if not os.path.exists(p):
            return p
        i += 1

def run_ffmpeg(cmd):
    """Запуск ffmpeg/ffprobe/ffplay с передачей списка аргументов; возвращает (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, text=True)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return 1, "", str(e)
