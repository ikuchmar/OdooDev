# -*- coding: utf-8 -*-
"""
thumbs_timeline.py — генерация ленты миниатюр по секундам и сохранение отдельных кадров.
"""
import os
import subprocess
from . import utils

def generate_thumbs_per_second(ffmpeg, video_path, out_dir, duration):
    """
    Генерируем кадр на каждую секунду.
    Реализация простая: вызываем ffmpeg для каждой секунды отдельно, чтобы избежать сложных фильтров.
    """
    duration = int(duration or 0)
    count = duration if duration > 0 else 0
    for sec in range(count):
        out = os.path.join(out_dir, f"thumb_{sec:06d}.png")
        # -y перезапись, -ss позиция, -vframes 1 — один кадр
        cmd = [ffmpeg, "-y", "-ss", str(sec), "-i", video_path, "-vframes", "1", "-vf", "scale=320:-1", out]
        utils.run_ffmpeg(cmd)
    return count

def save_frame(ffmpeg, video_path, sec, out_path):
    """Сохранить один кадр в PNG по заданной секунде."""
    cmd = [ffmpeg, "-y", "-ss", str(sec), "-i", video_path, "-vframes", "1", out_path]
    return utils.run_ffmpeg(cmd)
