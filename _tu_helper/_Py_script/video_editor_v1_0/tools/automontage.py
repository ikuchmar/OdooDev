# -*- coding: utf-8 -*-
"""
automontage.py — анализ тишины/застывшего кадра и вырезка/сжатие пауз.
Реализован простой анализ:
- По звуку: silencedetect (ищем участки с уровнем ниже порога).
- По картинке: freezedetect (ищем "зависшие" кадры дольше порога t).
"""
import os
import re
import tempfile
from . import utils, ffprobe_info

def _detect_silence(ffmpeg, video_path, silence_db=-35.0, minlen=1.0):
    # Получаем список t_start..t_end участков тишины
    cmd = [ffmpeg, "-i", video_path, "-af", f"silencedetect=noise={silence_db}dB:d={minlen}", "-f", "null", "-"]
    code, out, err = utils.run_ffmpeg(cmd)
    text = out + "\n" + err
    starts = [float(x) for x in re.findall(r"silence_start:\s*([0-9.]+)", text)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([0-9.]+)", text)]
    # Иногда количество start/end отличается; аккуратно сопоставим
    segs = []
    i = 0
    for s in starts:
        e = None
        # ищем следующий end, который больше s
        for j, val in enumerate(ends):
            if val is not None and val > s:
                e = val
                ends[j] = None
                break
        if e is not None:
            segs.append((s, e))
    return segs

def _detect_freeze(ffmpeg, video_path, freeze_t=2.0):
    # Ищем зависшие кадры (freezedetect) — выдаёт "freeze_start"/"freeze_end"
    cmd = [ffmpeg, "-i", video_path, "-vf", f"freezedetect=n=-60dB:d={freeze_t}", "-map", "0:v:0", "-f", "null", "-"]
    code, out, err = utils.run_ffmpeg(cmd)
    text = out + "\n" + err
    starts = [float(x) for x in re.findall(r"freeze_start:\s*([0-9.]+)", text)]
    ends = [float(x) for x in re.findall(r"freeze_end:\s*([0-9.]+)", text)]
    segs = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else None
        if e is not None:
            segs.append((s, e))
    return segs

def _expand_with_pad(segs, pad=0.2):
    # Добавляем запас до/после каждому сегменту
    return [(max(0.0, a - pad), b + pad) for (a, b) in segs]

def _intersect(a, b):
    # Пересечение двух списков сегментов по времени
    res = []
    for s1,e1 in a:
        for s2,e2 in b:
            s = max(s1,s2); e = min(e1,e2)
            if e > s:
                res.append((s,e))
    return res

def analyze(ffmpeg, video_path, mode="both", silence_db=-35.0, freeze_t=2.0, minlen=1.0, pad=0.2):
    # Возвращаем список сегментов (start,end), которые можно вырезать или сжать
    sil = _detect_silence(ffmpeg, video_path, silence_db=silence_db, minlen=minlen) if mode in ("audio","both") else []
    frz = _detect_freeze(ffmpeg, video_path, freeze_t=freeze_t) if mode in ("video","both") else []
    if mode == "both":
        segs = _intersect(sil, frz)
    elif mode == "audio":
        segs = sil
    else:
        segs = frz
    segs = _expand_with_pad(segs, pad=pad)
    # Слегка упорядочим и сольем пересечения
    segs.sort()
    merged = []
    for s,e in segs:
        if not merged or s > merged[-1][1]:
            merged.append([s,e])
        else:
            merged[-1][1] = max(merged[-1][1], e)
    return [(float(a), float(b)) for a,b in merged]

def parse_segments_text(text):
    """Парсим текст вида 'HH:MM:SS - HH:MM:SS' в список пар секунд."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    res = []
    for ln in lines:
        m = re.match(r"(\d{2}:\d{2}:\d{2})\s*-\s*(\d{2}:\d{2}:\d{2})", ln)
        if not m: continue
        from .utils import hhmmss_to_sec
        a = hhmmss_to_sec(m.group(1))
        b = hhmmss_to_sec(m.group(2))
        if b > a:
            res.append((a,b))
    return res

def apply(ffmpeg, video_path, segs, out_dir, mode="cut"):
    """
    Применяем автомонтаж:
    - mode='cut': вырезаем сегменты и склеиваем оставшееся (перекодирование для точности).
    - mode='compress': ускоряем сегменты в 4 раза и склеиваем.
    """
    base = os.path.splitext(os.path.basename(video_path))[0]
    out = utils.safe_out_path(out_dir, f"{base}_automontage", "mp4")

    # Строим фильтр: чередуем keep/modify сегменты.
    from .ffprobe_info import get_duration
    dur = get_duration("ffprobe", video_path) or 0.0

    # Готовим части
    parts = []
    cur = 0.0
    idx = 0
    for s,e in segs:
        if s > cur:
            parts.append(("keep", cur, s))
        parts.append(("mod", s, e))
        cur = e
    if cur < dur:
        parts.append(("keep", cur, dur))

    vf_parts = []
    af_parts = []
    for i,(kind,a,b) in enumerate(parts):
        if kind == "keep":
            vf_parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}]")
            af_parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}]")
        else:
            if mode == "cut":
                # Просто пропустим "mod" части (не добавляем их в вывод)
                continue
            else:
                # 'compress': ускорим в 4 раза
                vf_parts.append(f"[0:v]trim={a}:{b},setpts=(PTS-STARTPTS)/4[v{i}]")
                af_parts.append(f"[0:a]atrim={a}:{b},atempo=2,atempo=2,asetpts=PTS-STARTPTS[a{i}]")

    # Собираем concat
    vlabels = "".join(f"[v{i}]" for i,(k,_,_) in enumerate(parts) if not (k=='mod' and mode=='cut'))
    alabels = "".join(f"[a{i}]" for i,(k,_,_) in enumerate(parts) if not (k=='mod' and mode=='cut'))
    vf = ";".join(vf_parts + af_parts + [f"{vlabels}{alabels}concat=n={len(vlabels)//4}:v=1:a=1[outv][outa]"]) if vlabels else None

    if not vf:
        # если ничего не осталось, просто вернем исходник
        return video_path

    cmd = [ffmpeg, "-y", "-i", video_path, "-filter_complex", vf, "-map","[outv]","-map","[outa]",
           "-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-b:a","192k", out]
    utils.run_ffmpeg(cmd)
    return out
