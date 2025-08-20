# -*- coding: utf-8 -*-
"""
fragment_ops.py — вырезка/удаление фрагмента.
"""
import os
from . import utils

def extract_fragment(ffmpeg, video_path, start, end, out_dir, fast=True):
    """Сохранить выделенный фрагмент в новый файл."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_clip_{int(start)}-{int(end)}", "mp4")
    if fast:
        # Быстро: копирование потоков (без перекодирования). Может срезать по ключкадрам.
        cmd = [ffmpeg, "-y", "-ss", str(start), "-to", str(end), "-i", video_path, "-c", "copy", out]
    else:
        # Точно: перекодирование. Простой пресет H.264 + AAC.
        cmd = [ffmpeg, "-y", "-ss", str(start), "-to", str(end), "-i", video_path,
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-c:a", "aac", "-b:a", "192k", out]
    utils.run_ffmpeg(cmd)
    return out

def delete_fragment(ffmpeg, video_path, start, end, out_dir, fast=True):
    """Удалить выделенный фрагмент и склеить остальное."""
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_del_{int(start)}-{int(end)}", "mp4")
    if fast:
        # Вариант без перекодирования через concat demuxer (может требовать совпадения параметров)
        # Сформируем два фрагмента: [0..start) и (end..end_of_file]
        part1 = utils.safe_out_path(out_dir, f"{base}_part1_tmp", "mp4")
        part2 = utils.safe_out_path(out_dir, f"{base}_part2_tmp", "mp4")
        cmd1 = [ffmpeg, "-y", "-to", str(start), "-i", video_path, "-c", "copy", part1]
        cmd2 = [ffmpeg, "-y", "-ss", str(end), "-i", video_path, "-c", "copy", part2]
        utils.run_ffmpeg(cmd1); utils.run_ffmpeg(cmd2)
        # Конкат
        list_path = os.path.join(out_dir, f"{base}_concat_list.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            f.write(f"file '{part1}'\nfile '{part2}'\n")
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out]
        utils.run_ffmpeg(cmd)
        # Уберем временные
        try:
            os.remove(part1); os.remove(part2); os.remove(list_path)
        except Exception:
            pass
    else:
        # Перекодирование через фильтр trim/concat
        cmd = [ffmpeg, "-y", "-i", video_path,
               "-filter_complex",
               f"[0:v]trim=0:{start},setpts=PTS-STARTPTS[v0];"
               f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a0];"
               f"[0:v]trim={end}:,setpts=PTS-STARTPTS[v1];"
               f"[0:a]atrim={end}:,asetpts=PTS-STARTPTS[a1];"
               f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]",
               "-map","[outv]","-map","[outa]","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","192k", out]
        utils.run_ffmpeg(cmd)
    return out
