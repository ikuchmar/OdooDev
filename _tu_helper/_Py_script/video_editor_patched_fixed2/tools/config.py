# -*- coding: utf-8 -*-
"""
config.py — хранение и получение путей к ffmpeg/ffprobe/ffplay.
Просто пытаемся взять из PATH; при необходимости пользователь укажет вручную.
"""
import shutil

def get_ffmpeg_path():
    return shutil.which("ffmpeg")

def get_ffprobe_path():
    return shutil.which("ffprobe")

def get_ffplay_path():
    return shutil.which("ffplay")
