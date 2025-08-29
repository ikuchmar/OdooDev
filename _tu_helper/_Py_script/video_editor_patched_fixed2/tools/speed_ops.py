# -*- coding: utf-8 -*-
"""
speed_ops.py — изменение скорости видео и аудио, с вариантами "сохранять высоту" и "менять высоту".
"""
import os
from . import utils

def _atempo_chain(factor):
    """
    Фильтр atempo принимает значения в диапазоне [0.5..2.0].
    Для значений вне диапазона — разбиваем на несколько шагов (например, 4x = 2*2).
    """
    chain = []
    f = float(factor)
    if f == 0:
        f = 1.0
    if f < 0.5:
        # делим на части до диапазона
        while f < 0.5:
            chain.append("atempo=0.5")
            f /= 0.5
        chain.append(f"atempo={f:.4f}")
    elif f > 2.0:
        while f > 2.0:
            chain.append("atempo=2.0")
            f /= 2.0
        chain.append(f"atempo={f:.4f}")
    else:
        chain.append(f"atempo={f:.4f}")
    return ",".join(chain)

def apply_speed(ffmpeg, video_path, out_dir, factor=1.5, pitch_mode="preserve", scope="all", start=None, end=None):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_speed_{factor:g}", "mp4")

    # Видео ускорим/замедлим через setpts (PTS/коэф)
    v_filter = f"setpts=PTS/{factor:.6f}"
    # Аудио: preserve = atempo, change = asetrate+aresample
    if pitch_mode == "preserve":
        a_filter = _atempo_chain(factor)
    else:
        a_filter = f"asetrate=44100*{factor:.6f},aresample=44100"

    if scope == "fragment" and start is not None and end is not None:
        # Разрежем на 3 части и изменим скорость только внутри окна
        vf = (f"[0:v]trim=0:{start},setpts=PTS-STARTPTS[v0];"
              f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a0];"
              f"[0:v]trim={start}:{end},{v_filter},setpts=PTS-STARTPTS[v1];"
              f"[0:a]atrim={start}:{end},{a_filter},asetpts=PTS-STARTPTS[a1];"
              f"[0:v]trim={end}:,setpts=PTS-STARTPTS[v2];"
              f"[0:a]atrim={end}:,asetpts=PTS-STARTPTS[a2];"
              f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[outv][outa]")
        cmd = [ffmpeg, "-y", "-i", video_path, "-filter_complex", vf, "-map","[outv]","-map","[outa]",
               "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","192k", out]
    else:
        cmd = [ffmpeg, "-y", "-i", video_path, "-filter_complex", f"[0:v]{v_filter}[v];[0:a]{a_filter}[a]",
               "-map","[v]","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","192k", out]
    utils.run_ffmpeg(cmd)
    return out
