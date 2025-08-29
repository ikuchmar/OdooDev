# -*- coding: utf-8 -*-
"""
player_control.py — управление просмотром через ffplay.
"""
import subprocess

def open_player(ffplay, video_path, start_sec=0.0):
    """
    Открыть окно плеера ffplay, начиная с заданного времени.
    Кнопки ffplay: Space — пауза, ←/→ — +-10 сек, ↑/↓ — громкость.
    """
    start = max(0.0, float(start_sec or 0.0))
    # -autoexit чтобы окно само закрывалось по окончании видео
    # -ss до -i у ffplay работает как начальная позиция
    cmd = [ffplay, "-autoexit", "-ss", str(start), "-i", video_path]
    subprocess.Popen(cmd)
