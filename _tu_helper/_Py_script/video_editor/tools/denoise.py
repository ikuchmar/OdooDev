# -*- coding: utf-8 -*-
"""
denoise.py — шумоподавление аудио.
Пресеты реализованы через afftdn (частотно-временное подавление) как базовый вариант.
Если у пользователя есть модель RNNoise (.onnx/.model для arnndn), можно расширить.
"""
import os
from . import utils

def _preset_to_afftdn(preset):
    # Простое соответствие: чем сильнее — тем выше шумоподавление (nr).
    if preset == "light":
        return "afftdn=nr=12"
    if preset == "strong":
        return "afftdn=nr=24"
    return "afftdn=nr=18"  # medium

def apply_denoise(ffmpeg, video_path, out_dir, preset="medium", scope="all", start=None, end=None):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_denoise_{preset}", "mp4")
    af = _preset_to_afftdn(preset)
    if scope == "fragment" and start is not None and end is not None:
        # Применим фильтр только в окне start..end
        af = f"[0:a]asplit[a][b];[a]{af}:enable='between(t,{start},{end})'[a1];[b]anull[a2];[a1][a2]amix=inputs=2:duration=longest[aout]"
        cmd = [ffmpeg, "-y", "-i", video_path, "-filter_complex", af, "-map", "0:v", "-map", "[aout]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out]
    else:
        cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "copy", "-af", af, "-c:a", "aac", "-b:a", "192k", out]
    utils.run_ffmpeg(cmd)
    return out
