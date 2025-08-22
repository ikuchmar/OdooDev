# video_editor/tools/fragment_ops.py
# -*- coding: utf-8 -*-
"""
fragment_ops.py — операции вырезания/сохранения нескольких интервалов.

Ключевые функции:
- normalize_intervals(segs, duration)       -> сортирует, обрезает в границы, склеивает пересечения
- invert_intervals(segs, duration)          -> возвращает список "оставшихся" интервалов
- keep_only_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=0.0)
- cut_out_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=0.0)

Реализация вырезки/склейки:
- Используем один прогон FFmpeg с filter_complex: trim/atrim + concat (v=1,a=1).
- Это точнее и надёжнее, чем много раз "копировать" куски и потом демультиплексировать.
- Если в видео нет аудио — строим граф только для видео (v=1,a=0).

Выход:
- Всегда перекодирование в H.264 + AAC (совместимость), CRF=22, preset=veryfast, yuv420p, 48 kHz.
"""

import os
import subprocess
from . import ffprobe_info, utils


# ----------------------------------------------------------------------
# Вспомогательные функции
# ----------------------------------------------------------------------
def _run(args):
    """Простой запуск внешней команды, возвращает (код_выхода, stdout, stderr) как строки."""
    try:
        cp = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, encoding="utf-8", errors="ignore")
        return cp.returncode, cp.stdout, cp.stderr
    except Exception as e:
        return 1, "", str(e)

def _has_audio(ffprobe, path):
    """
    Проверяем наличие аудиопотока через ffprobe.
    Возвращаем True/False.
    """
    rc, out, _ = _run([
        ffprobe, "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        path
    ])
    return (rc == 0) and (out.strip() != "")

def _safe_basename_noext(path):
    """Имя файла без расширения, безопасное для формирования имени вывода."""
    base = os.path.basename(path)
    name, _ext = os.path.splitext(base)
    return name or "output"

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

# ----------------------------------------------------------------------
# Нормализация списков интервалов
# ----------------------------------------------------------------------
def normalize_intervals(segs, duration=0.0):
    """
    Принимает список [(s,e), ...] в секундах.
    1) Обрезает в диапазон [0, duration] (если duration>0),
    2) отбрасывает пустые/отрицательные,
    3) сортирует по началу,
    4) склеивает пересекающиеся/соприкасающиеся интервалы.
    Возвращает новый список [(s,e), ...].
    """
    res = []
    for s, e in segs:
        s = float(s); e = float(e)
        if duration and duration > 0:
            s = _clamp(s, 0.0, duration)
            e = _clamp(e, 0.0, duration)
        if e <= s:
            continue
        res.append((s, e))
    if not res:
        return []

    # Сортировка
    res.sort(key=lambda x: x[0])

    # Склейка
    merged = []
    cs, ce = res[0]
    for s, e in res[1:]:
        if s <= ce + 1e-6:  # соприкасаются/перекрываются
            ce = max(ce, e)
        else:
            merged.append((cs, ce))
            cs, ce = s, e
    merged.append((cs, ce))
    return merged

def invert_intervals(segs, duration):
    """
    Из списка "вырезать" строит список "оставить" как дополнение на [0, duration].
    """
    duration = max(0.0, float(duration or 0.0))
    if duration <= 0:
        return []

    segs = normalize_intervals(segs, duration)
    if not segs:
        return [(0.0, duration)]

    keep = []
    cur = 0.0
    for s, e in segs:
        if s > cur + 1e-9:
            keep.append((cur, s))
        cur = max(cur, e)
    if cur < duration:
        keep.append((cur, duration))
    return keep

# ----------------------------------------------------------------------
# Построение filter_complex для concat из списка интервалов
# ----------------------------------------------------------------------
def _build_concat_filter(keep_segs, with_audio=True):
    """
    Строит filter_complex для склейки списка интервалов keep_segs.
    Возвращает кортеж: (filter_complex_str, map_args_list)
      - map_args_list — список аргументов -map, например ['-map','[v]','-map','[a]'] или только ['-map','[v]'].

    Идея:
    [0:v]trim=start=a:end=b,setpts=PTS-STARTPTS[v0];
    [0:a]atrim=start=a:end=b,asetpts=PTS-STARTPTS[a0];
    ...
    [v0][a0][v1][a1]concat=n=N:v=1:a=1[v][a]
    """
    parts = []
    n = len(keep_segs)

    # Генерируем блоки trim/atrim
    for i, (s, e) in enumerate(keep_segs):
        s_str = f"{max(0.0, float(s)):.6f}".rstrip('0').rstrip('.')
        e_str = f"{max(0.0, float(e)):.6f}".rstrip('0').rstrip('.')
        parts.append(f"[0:v]trim=start={s_str}:end={e_str},setpts=PTS-STARTPTS[v{i}]")
        if with_audio:
            parts.append(f"[0:a]atrim=start={s_str}:end={e_str},asetpts=PTS-STARTPTS[a{i}]")

    # Генерируем финальный concat
    if with_audio:
        mid = "".join(f"[v{i}][a{i}]" for i in range(n))
        parts.append(f"{mid}concat=n={n}:v=1:a=1[v][a]")
        maps = ["-map", "[v]", "-map", "[a]"]
    else:
        mid = "".join(f"[v{i}]" for i in range(n))
        parts.append(f"{mid}concat=n={n}:v=1:a=0[v]")
        maps = ["-map", "[v]"]

    return ";".join(parts), maps

# ----------------------------------------------------------------------
# Основные операции
# ----------------------------------------------------------------------
def keep_only_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=0.0):
    """
    Сохраняет только указанные интервалы `segs` (в секундах) и склеивает их в один файл.
    Возвращает путь к готовому файлу.
    """
    # Нормализуем интервалы с учётом длительности (если известна)
    duration = duration_hint or ffprobe_info.get_duration(ffprobe, src) or 0.0
    keep = normalize_intervals(segs, duration)

    if not keep:
        # Нечего сохранять — создаём крошечный пустой фрагмент (или сообщаем)
        raise RuntimeError("Список интервалов пуст после нормализации.")

    # Проверяем наличие аудио
    with_audio = _has_audio(ffprobe, src)

    # Собираем filter_complex
    fc, maps = _build_concat_filter(keep, with_audio=with_audio)

    # Готовим выходной путь
    base = _safe_basename_noext(src)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{base}_keep_segments.mp4")

    # Команда FFmpeg
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", src,
        "-filter_complex", fc,
        *maps,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
    ]
    if with_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        cmd += ["-an"]
    cmd += [out]

    rc, _stdout, stderr = _run(cmd)
    if rc != 0:
        # Для простоты отдадим stderr пользователю через исключение
        raise RuntimeError(f"FFmpeg error (keep_only_segments): {stderr.strip() or rc}")
    return out


def cut_out_segments(ffmpeg, ffprobe, src, segs, outdir, duration_hint=0.0):
    """
    Удаляет (вырезает) все интервалы `segs`, а оставшееся склеивает в один файл.
    Возвращает путь к готовому файлу.
    """
    # Определяем длительность (нужно для дополнения)
    duration = duration_hint or ffprobe_info.get_duration(ffprobe, src) or 0.0

    # Инвертируем интервалы: что оставить после вырезания
    keep = invert_intervals(segs, duration)
    if not keep:
        raise RuntimeError("После вырезания фрагментов ничего не остаётся.")

    # Проверяем наличие аудио
    with_audio = _has_audio(ffprobe, src)

    # filter_complex
    fc, maps = _build_concat_filter(keep, with_audio=with_audio)

    # Выходной файл
    base = _safe_basename_noext(src)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{base}_cut_removed.mp4")

    # Команда FFmpeg
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", src,
        "-filter_complex", fc,
        *maps,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
    ]
    if with_audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        cmd += ["-an"]
    cmd += [out]

    rc, _stdout, stderr = _run(cmd)
    if rc != 0:
        raise RuntimeError(f"FFmpeg error (cut_out_segments): {stderr.strip() or rc}")
    return out
