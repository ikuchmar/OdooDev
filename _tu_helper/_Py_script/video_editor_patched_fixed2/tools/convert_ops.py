# -*- coding: utf-8 -*-
"""
convert_ops.py — конвертация/перекодирование/ремакс.
"""
import os
from . import utils

def _scale_to_size(scale):
    if scale == "2160p": return "3840:2160"
    if scale == "1440p": return "2560:1440"
    if scale == "1080p": return "1920:1080"
    if scale == "720p":  return "1280:720"
    if scale == "480p":  return "854:480"
    return None

def convert_video(ffmpeg, video_path, out_dir, fmt="mp4", quality="medium", scale="keep"):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_conv", fmt)
    # Профили качества через CRF
    crf = {"original": "18", "large": "20", "medium": "23", "small": "28"}.get(quality, "23")
    vf = ["format=yuv420p"]
    size = _scale_to_size(scale)
    if size:
        vf.insert(0, f"scale={size}")
    vf_str = ",".join(vf)
    cmd = [ffmpeg, "-y", "-i", video_path, "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
           "-vf", vf_str, "-c:a", "aac", "-b:a", "192k", out]
    utils.run_ffmpeg(cmd)
    return out

def remux_video(ffmpeg, video_path, out_dir, fmt="mkv"):
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_remux", fmt)
    cmd = [ffmpeg, "-y", "-i", video_path, "-c", "copy", out]
    utils.run_ffmpeg(cmd)
    return out
