# -*- coding: utf-8 -*-
"""
logo_overlay.py — наложение прозрачного PNG-логотипа на видео.
"""
import os
from . import utils

def _pos_to_xy(pos):
    # Возвращаем выражения для overlay x,y
    if pos == "top-left":
        return "10", "10"
    if pos == "top-right":
        return "main_w-overlay_w-10", "10"
    if pos == "bottom-left":
        return "10", "main_h-overlay_h-10"
    # bottom-right
    return "main_w-overlay_w-10", "main_h-overlay_h-10"

def apply_logo(ffmpeg, video_path, out_dir, logo_path, pos, scale_pct, scope="all", start=None, end=None):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_logo", "mp4")
    x, y = _pos_to_xy(pos)
    # Масштаб логотипа относительно ширины видео: scale2ref поможет автомасштабировать
    filt = (f"[1][0]scale2ref=w=iw*{scale_pct}/100:h=ow/mdar[lg][bg];"
            f"[bg][lg]overlay={x}:{y}")

    if scope == "fragment" and start is not None and end is not None:
        # Наложим логотип только в окне времени через enable=between(t,...)
        filt = (f"[1][0]scale2ref=w=iw*{scale_pct}/100:h=ow/mdar[lg][bg];"
                f"[bg][lg]overlay={x}:{y}:enable='between(t,{start},{end})'")
    cmd = [ffmpeg, "-y", "-i", video_path, "-i", logo_path, "-filter_complex", filt,
           "-map","0:v","-map","0:a?","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","192k", out]
    utils.run_ffmpeg(cmd)
    return out
