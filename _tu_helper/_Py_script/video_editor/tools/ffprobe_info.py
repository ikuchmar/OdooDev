# -*- coding: utf-8 -*-
"""
ffprobe_info.py — функции для получения метаданных через ffprobe (длительность и пр.).
"""
import json
import subprocess

def get_duration(ffprobe_path, video_path):
    """Возвращает длительность в секундах (float) или None."""
    try:
        cmd = [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        data = json.loads(out)
        dur = float(data.get("format", {}).get("duration", 0.0))
        return dur
    except Exception:
        return None
