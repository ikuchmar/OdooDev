# video_editor/tools/config_store.py
# -*- coding: utf-8 -*-
"""
config_store.py — простое хранилище настроек проекта в INI-файле (app.conf).
Файл: video_editor/app.conf

Секции по умолчанию:
[app]    last_video
[audio]  base_height, view_height, px_per_sec, zoom, show_video
[tools]  ffmpeg, ffprobe, ffplay
"""
import os
import configparser

_DEF = {
    "app": {
        "last_video": ""
    },
    "audio": {
        "base_height": "500",
        "view_height": "220",
        "px_per_sec": "10",
        "zoom": "1.0",
        "show_video": "true",
    },
    "tools": {
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
        "ffplay": "ffplay",
    },
}

def _config_path():
    here = os.path.dirname(__file__)
    root = os.path.abspath(os.path.join(here, ".."))
    return os.path.join(root, "app.conf")

def _ensure_defaults(cfg):
    for sec, kv in _DEF.items():
        if not cfg.has_section(sec):
            cfg.add_section(sec)
        for k, v in kv.items():
            if not cfg.has_option(sec, k):
                cfg.set(sec, k, v)

def load():
    path = _config_path()
    cfg = configparser.ConfigParser()
    if os.path.exists(path):
        try:
            cfg.read(path, encoding="utf-8")
        except Exception:
            cfg = configparser.ConfigParser()
    _ensure_defaults(cfg)
    return cfg, path

def save(cfg):
    path = _config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            cfg.write(f)
        return True
    except Exception:
        return False

def get(section, key, default=None):
    cfg, _ = load()
    try:
        return cfg.get(section, key)
    except Exception:
        return default

def set(section, key, value):
    cfg, _ = load()
    if not cfg.has_section(section):
        cfg.add_section(section)
    cfg.set(section, key, str(value))
    save(cfg)

def get_bool(section, key, default=False):
    val = get(section, key, None)
    if val is None:
        return bool(default)
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def get_int(section, key, default=0):
    val = get(section, key, None)
    try:
        return int(val)
    except Exception:
        return int(default)

def get_float(section, key, default=0.0):
    val = get(section, key, None)
    try:
        return float(val)
    except Exception:
        return float(default)
