# video_editor/tools/thumbs_timeline.py
# -*- coding: utf-8 -*-
"""
thumbs_timeline.py — генерация миниатюр ленты и сохранение кадров через FFmpeg.

Функции:
- generate_thumbs_per_second(ffmpeg, src, outdir, duration): миниатюры каждую секунду (быстро)
- generate_thumbs_step(ffmpeg, src, outdir, duration, step_sec): миниатюры каждые N секунд (быстро)
- generate_thumbs_step_iter(ffmpeg, src, outdir, duration, step_sec): надёжный режим (медленнее)
- save_frame(ffmpeg, src, sec, out_png): сохранить кадр на заданной секунде
"""
import os
import glob
import shutil
import subprocess

def _run(cmd):
    """Запускает внешнюю команду и возвращает код возврата."""
    try:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False).returncode
    except Exception:
        return 1

def _cleanup_pattern(pattern):
    """Удаляет ранее созданные файлы по шаблону (если есть)."""
    for p in glob.glob(pattern):
        try:
            os.remove(p)
        except Exception:
            pass

# -------- Быстрый режим (через fps) --------

def generate_thumbs_per_second(ffmpeg, src, outdir, duration):
    """Сгенерировать миниатюры каждую секунду (делегирует на шаг=1)."""
    return generate_thumbs_step(ffmpeg, src, outdir, duration, step_sec=1)

def generate_thumbs_step(ffmpeg, src, outdir, duration, step_sec=10):
    """
    Делает миниатюры каждые N секунд (быстро, через фильтр fps=1/step).
    Создаёт временные файлы tmp_thumb_%06d.png, затем переименовывает в thumb_{секунда:06d}.png.
    Возвращает ФАКТИЧЕСКОЕ количество созданных миниатюр (int).
    """
    step = max(1, int(step_sec))

    _cleanup_pattern(os.path.join(outdir, "thumb_*.png"))
    _cleanup_pattern(os.path.join(outdir, "tmp_thumb_*.png"))

    tmp_pattern = os.path.join(outdir, "tmp_thumb_%06d.png")
    vf = f"fps=1/{step},scale=320:-2"
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", src,
        "-vf", vf,
        "-vsync", "vfr",
        tmp_pattern
    ]
    rc = _run(cmd)
    if rc != 0:
        return 0

    tmp_files = sorted(glob.glob(os.path.join(outdir, "tmp_thumb_*.png")))
    count = len(tmp_files)
    if count == 0:
        return 0

    # Переименовываем по факту: индекс i (с 1) -> секунда (i-1)*step
    for i, tmp_path in enumerate(tmp_files, start=1):
        sec_mark = (i - 1) * step
        new_name = os.path.join(outdir, f"thumb_{sec_mark:06d}.png")
        try:
            os.replace(tmp_path, new_name)
        except Exception:
            try:
                shutil.copy2(tmp_path, new_name)
                os.remove(tmp_path)
            except Exception:
                pass

    return count

# -------- Надёжный режим (кадр через -ss) --------

def generate_thumbs_step_iter(ffmpeg, src, outdir, duration, step_sec=10):
    """
    Надёжный режим: извлекаем по одному кадру на каждом шаге через -ss (быстрее seek до ключевых кадров).
    Медленнее, но гарантированно покрывает весь ролик.
    Имена файлов: thumb_{секунда:06d}.png

    Возвращает количество успешно созданных миниатюр.
    """
    step = max(1, int(step_sec))

    _cleanup_pattern(os.path.join(outdir, "thumb_*.png"))

    total = 0
    end_sec = max(0, int(duration))
    # Ряд секунд: 0, step, 2*step, ..., <= end_sec
    sec_list = list(range(0, end_sec + 1, step))
    if not sec_list:
        sec_list = [0]

    for sec in sec_list:
        out_png = os.path.join(outdir, f"thumb_{sec:06d}.png")
        # -ss до входа: быстрый seek к ближайшему ключевому кадру; достаточно для миниатюры
        cmd = [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-y",
            "-ss", str(sec),
            "-i", src,
            "-frames:v", "1",
            "-vf", "scale=320:-2",
            out_png
        ]
        rc = _run(cmd)
        if rc == 0 and os.path.exists(out_png):
            total += 1

    return total

# -------- Точное сохранение одиночного кадра --------

def save_frame(ffmpeg, src, sec, out_png):
    """
    Сохранить точный кадр на заданной секунде в PNG.
    Используем -ss до входа + -frames:v 1 для быстрой выборки.
    """
    sec = max(0, int(sec))
    os.makedirs(os.path.dirname(out_png) or ".", exist_ok=True)
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y",
        "-ss", str(sec),
        "-i", src,
        "-frames:v", "1",
        "-vf", "scale=1280:-2",
        out_png
    ]
    return _run(cmd) == 0
