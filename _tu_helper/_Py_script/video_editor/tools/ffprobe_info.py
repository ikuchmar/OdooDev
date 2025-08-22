# -*- coding: utf-8 -*-
"""
ffprobe_info.py — утилиты для извлечения метаданных через ffprobe.
Главная функция: get_duration(ffprobe, path) -> float (секунды)
"""
import subprocess

def _run(args):
    try:
        cp = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, encoding="utf-8", errors="ignore")
        return cp.stdout.strip(), cp.returncode
    except Exception:
        return "", 1

def _parse_time_to_seconds(s):
    """Пробуем распарсить число или формат HH:MM:SS(.ms)."""
    if not s:
        return None
    s = s.strip()
    try:
        return float(s)
    except Exception:
        pass
    if ":" in s:
        try:
            parts = s.split(":")
            sec = 0.0
            for p in parts:
                sec = sec * 60.0 + float(p)
            return sec
        except Exception:
            return None
    return None

def get_duration(ffprobe, path):
    """
    Возвращает длительность файла в секундах (float) или 0.0 при неудаче.
    Стратегия:
      1) format=duration (десятичные секунды)
      2) format=duration с -sexagesimal (HH:MM:SS.ms)
      3) stream=duration по всем потокам — берём максимум
    """
    # 1) format=duration (десятичные секунды)
    out, rc = _run([ffprobe, "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=nokey=1:noprint_wrappers=1",
                    path])
    dur = _parse_time_to_seconds(out)
    if rc == 0 and dur and dur > 0:
        return float(dur)

    # 2) тот же параметр, но sexagesimal
    out, rc = _run([ffprobe, "-v", "error",
                    "-sexagesimal",
                    "-show_entries", "format=duration",
                    "-of", "default=nokey=1:noprint_wrappers=1",
                    path])
    dur = _parse_time_to_seconds(out)
    if rc == 0 and dur and dur > 0:
        return float(dur)

    # 3) максимум среди stream=duration
    out, rc = _run([ffprobe, "-v", "error",
                    "-show_entries", "stream=duration",
                    "-of", "default=nokey=1:noprint_wrappers=1",
                    path])
    best = 0.0
    if rc == 0 and out:
        for line in out.splitlines():
            val = _parse_time_to_seconds(line)
            if val and val > best:
                best = float(val)
    return best if best > 0 else 0.0
