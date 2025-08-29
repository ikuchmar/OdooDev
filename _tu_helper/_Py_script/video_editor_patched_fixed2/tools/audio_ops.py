# -*- coding: utf-8 -*-
"""
audio_ops.py — операции со звуком: удалить, заглушить фрагмент, заменить из файла/микрофона,
смешать поверх, нормализация (простая и EBU R128 в 2 прохода).
"""
import os
import subprocess
import tempfile
from . import utils

def remove_audio_all(ffmpeg, video_path, out_dir):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_nosound", "mp4")
    cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-an", out]
    utils.run_ffmpeg(cmd)
    return out

def mute_audio_fragment(ffmpeg, video_path, start, end, out_dir):
    """Сделать тишину внутри фрагмента, остальное без изменений (перекодирование аудио)."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_mute_{int(start)}-{int(end)}", "mp4")
    # Установим громкость 0 в окне между start..end: volume=enable='between(t,start,end)':volume=0
    af = f"volume=enable='between(t,{start},{end})':volume=0"
    cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", out]
    utils.run_ffmpeg(cmd)
    return out

def replace_audio_full(ffmpeg, video_path, audio_path, out_dir):
    """Полная замена звука аудио-дорожкой из файла; обрежем по короткому (shortest)."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_audio_replaced", "mp4")
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", audio_path, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    utils.run_ffmpeg(cmd)
    return out

def replace_audio_from_mic(ffmpeg, video_path, out_dir, dur_sec=10):
    """
    Простейшая запись с системного устройства по умолчанию (может отличаться на ОС).
    Для кроссплатформенности оставляем как пример с 5 сек. записи; при необходимости выбрать устройство.
    """
    base = os.path.splitext(os.path.basename(video_path))[0]
    tmp_wav = os.path.join(out_dir, f"{base}_mic_tmp.wav")
    # Попытаемся угадать команду записи для разных ОС:
    if os.name == "nt":
        # Windows: DirectShow (устройство "audio=default" может не существовать — пользователь подстроит вручную).
        rec_cmd = [ffmpeg, "-y", "-f", "dshow", "-t", str(dur_sec), "-i", "audio=default", tmp_wav]
    elif sys.platform == "darwin":
        # macOS: avfoundation, устройство 0:0 обычно дефолт (может отличаться).
        rec_cmd = [ffmpeg, "-y", "-f", "avfoundation", "-t", str(dur_sec), "-i", ":0", tmp_wav]
    else:
        # Linux: pulse по умолчанию
        rec_cmd = [ffmpeg, "-y", "-f", "pulse", "-t", str(dur_sec), "-i", "default", tmp_wav]

    utils.run_ffmpeg(rec_cmd)

    out = utils.safe_out_path(out_dir, f"{base}_mic_replaced", "mp4")
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", tmp_wav, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    utils.run_ffmpeg(cmd)
    try:
        os.remove(tmp_wav)
    except Exception:
        pass
    return out

def mix_audio_overlay(ffmpeg, video_path, audio_path, out_dir, ducking_db=8):
    """Смешать поверх оригинала новый звук; легкий дукинг оригинала в моменты звучания оверлея."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_mixed", "mp4")
    # Сведем два аудиопотока, слегка приглушая оригинал (sidechaincompressor имитируем компрессором с ducking).
    # Избегаем сложных фильтров: просто уменьшим уровень оригинала на 6 дБ, а оверлей оставим 0 дБ.
    af = f"[0:a]volume=0.7[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:dropout_transition=0:normalize=0[aout]"
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", audio_path, "-filter_complex", af, "-map", "0:v", "-map", "[aout]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
    utils.run_ffmpeg(cmd)
    return out

def normalize_audio(ffmpeg, video_path, out_dir, mode="fast"):
    base = os.path.splitext(os.path.basename(video_path))[0]
    if mode == "fast":
        out = utils.safe_out_path(out_dir, f"{base}_norm_fast", "mp4")
        # Быстрый вариант: динамическая нормализация (dynaudnorm)
        cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-af", "dynaudnorm", "-c:a", "aac", "-b:a", "192k", out]
        utils.run_ffmpeg(cmd)
        return out

    # EBU R128 — 2 прохода: сначала собираем статистику
    stats = os.path.join(out_dir, f"{base}_loudnorm_stats.txt")
    cmd1 = [ffmpeg, "-y", "-i", video_path, "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json", "-f", "null", "-"]
    code, out1, err1 = utils.run_ffmpeg(cmd1)
    text = out1 + "\n" + err1
    # Ищем JSON c измерениями
    import re, json
    m = re.search(r'\{[\s\S]*?"measured_I"[\s\S]*?\}', text)
    if not m:
        # fallback: однопроходная нормализация
        out = utils.safe_out_path(out_dir, f"{base}_norm_ebu", "mp4")
        cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy",
               "-af", "loudnorm=I=-16:LRA=11:TP=-1.5", "-c:a", "aac", "-b:a", "192k", out]
        utils.run_ffmpeg(cmd)
        return out
    j = json.loads(m.group(0))
    # Второй проход с параметрами измерений
    out = utils.safe_out_path(out_dir, f"{base}_norm_ebu", "mp4")
    af = ("loudnorm=I=-16:LRA=11:TP=-1.5:"
          f"measured_I={j.get('measured_I')}:measured_LRA={j.get('measured_LRA')}:measured_TP={j.get('measured_TP')}:"
          f"measured_thresh={j.get('measured_thresh')}:offset={j.get('target_offset')}")
    cmd2 = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", out]
    utils.run_ffmpeg(cmd2)
    return out
