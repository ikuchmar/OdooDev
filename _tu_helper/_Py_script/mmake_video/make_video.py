#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_video.py — простой и подробно прокомментированный скрипт,
который собирает видео из:
  • изображений (слайд-шоу, переходы),
  • аудио (два режима: 'sequence' — последовательно, 'mix' — параллельно),
  • субтитров (soft/дорожка или burn/прожиг; можно отключить через subtitles.enable),
  • текстовых оверлеев (белый текст из .txt поверх кадра).

Главный фикс: drawtext теперь получает текст из Python через text='…'
(а НЕ через textfile=…), что устраняет проблемы кавычек/двоеточий на Windows.

Как запускать:
  1) Положите 'make_video.py' и 'config.toml' в одну папку.
  2) Запустите:   python make_video.py        (или --dry-run / --verbose)
Требования: Python 3.11+ (tomllib), установленный ffmpeg в PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import tomllib  # стандартный парсер TOML (Python 3.11+)

# ====================== ВСПОМОГАТЕЛЬНЫЕ ======================

def log(msg: str) -> None:
    print(msg)

def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)

def check_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        die(
            "ffmpeg не найден в PATH. Установите его и/или добавьте в PATH.\n"
            "Windows: https://www.gyan.dev/ffmpeg/builds/\n"
            "macOS (Homebrew): brew install ffmpeg\n"
            "Linux (Debian/Ubuntu): sudo apt-get install ffmpeg"
        )

def default_config_path() -> Path:
    return Path(__file__).resolve().parent / "config.toml"

# --- Экранирование текста для drawtext:text='…'
def escape_drawtext_text(s: str) -> str:
    """
    Минимально необходимое экранирование для drawtext:
      - обратный слэш -> \\\\
      - одинарная кавычка -> \'
      - двоеточие -> \:
      - перевод строки -> \\n
      - возврат каретки -> \\n (заменим)
    Этого достаточно для безопасной передачи в text='…' внутри filter_complex.
    """
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace(":", "\\:")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", r"\n")
    return s

# ====================== СТРУКТУРЫ ДАННЫХ ======================

@dataclass
class ImageItem:
    path: Path
    start: Optional[float] = None
    duration: Optional[float] = None
    transition: Optional[str] = None  # "none"|"crossfade"|"dip"|None

@dataclass
class AudioItem:
    path: Path
    start: Optional[float] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    gain_db: Optional[float] = None

@dataclass
class SubItem:
    path: Path

@dataclass
class TextItem:
    path: Path
    start: Optional[float] = None
    end: Optional[float] = None
    x: Optional[str] = None
    y: Optional[str] = None
    fontsize: Optional[int] = None
    line_spacing: Optional[int] = None
    box: Optional[bool] = None
    boxcolor: Optional[str] = None
    boxborderw: Optional[int] = None
    fontcolor: Optional[str] = None
    shadowcolor: Optional[str] = None
    shadowx: Optional[int] = None
    shadowy: Optional[int] = None

@dataclass
class Config:
    # Выход
    out_filename: Path
    overwrite: bool
    sidecar_timeline: bool
    # Видео
    resolution: str
    fps: int
    bg_mode: str
    bg_color: str
    default_image_duration: float
    # Переходы
    tr_type: str
    tr_duration: float
    # Изображения
    img_use_folder: bool
    img_folder: Path
    img_order: str
    img_list: List[ImageItem]
    # Аудио
    aud_mode: str  # "sequence" | "mix"
    aud_use_folder: bool
    aud_folder: Path
    aud_order: str
    aud_list: List[AudioItem]
    # Нормализация аудио
    norm_mode: str
    norm_target: float
    # Субтитры
    sub_enable: bool
    sub_mode: str
    sub_encoding: str
    sub_select_strategy: str
    sub_allow_list: bool
    sub_file: Optional[Path]
    sub_folder: Path
    sub_list: List[SubItem]
    sub_style_preset: str
    # Текст-оверлей
    text_enable: bool
    text_fontfile: str
    text_use_folder: bool
    text_folder: Path
    text_order: str
    text_bind_to_images: bool
    text_defaults: dict
    text_list: List[TextItem]
    # Заглушки/безопасность
    ph_image_path: Optional[Path]
    ph_image_text: str
    ph_audio_silence_enable: bool
    ph_audio_silence_db: float
    safety_stop_on_missing: bool
    safety_fallback_image: Optional[Path]
    # Прочее
    timing_snap: bool
    timing_offset: float
    log_level: str
    log_to_file: bool

# ====================== ЗАГРУЗКА КОНФИГА ======================

def load_config(path: Path) -> Config:
    if not path.exists():
        die(f"Файл конфига не найден: {path}\n"
            f"Подсказка: положите 'config.toml' рядом со скриптом "
            f"или передайте путь через --config")

    with path.open("rb") as f:
        data = tomllib.load(f)

    def g(dct, key, default=None):
        return dct.get(key, default)

    output = data.get("output", {})
    video = data.get("video", {})
    video_bg = video.get("background", {})
    tr = data.get("transitions_default", {})
    images = data.get("images", {})
    audio = data.get("audio", {})
    audio_norm = data.get("audio_normalize", {})
    subs = data.get("subtitles", {})
    subs_style = subs.get("style", {})
    textov = data.get("text_overlay", {})
    placeholders = data.get("placeholders", {})
    ph_img = placeholders.get("image", {})
    ph_aud = data.get("audio_silence", {})
    safety = data.get("safety", {})
    timing = data.get("timing", {})
    logging_cfg = data.get("logging", {})

    # Выход
    out_filename = Path(g(output, "filename", "output.mp4"))
    overwrite = bool(g(output, "overwrite", False))
    sidecar = bool(g(output, "sidecar_timeline", False))

    # Видео
    resolution = str(g(video, "resolution", "1080p")).lower()
    fps = int(g(video, "fps", 30))
    default_img_dur = float(g(video, "default_image_duration", 3.0))
    bg_mode = str(g(video_bg, "mode", "contain")).lower()
    bg_color = str(g(video_bg, "color", "black"))

    # Переходы
    tr_type = str(g(tr, "type", "none")).lower()
    tr_duration = float(g(tr, "duration", 0.5))

    # Изображения
    img_use_folder = bool(g(images, "use_folder", True))
    img_folder = Path(g(images, "folder", "./images"))
    img_order = str(g(images, "order", "by_name")).lower()
    img_list_raw = g(images, "list", []) or []

    img_items: List[ImageItem] = []
    if img_use_folder:
        if img_folder.exists():
            files = sorted([p for p in img_folder.iterdir() if p.is_file()],
                           key=lambda p: p.name.lower())
            for p in files:
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                    img_items.append(ImageItem(path=p))
        else:
            log(f"WARNING: папка с изображениями не найдена: {img_folder}")
    else:
        for row in img_list_raw:
            img_items.append(ImageItem(
                path=Path(str(row.get("path", ""))),
                start=row.get("start", None),
                duration=row.get("duration", None),
                transition=row.get("transition", None),
            ))

    # Аудио
    aud_mode = str(g(audio, "mode", "sequence")).lower()
    aud_use_folder = bool(g(audio, "use_folder", True))
    aud_folder = Path(g(audio, "folder", "./audio"))
    aud_order = str(g(audio, "order", "by_name")).lower()
    aud_list_raw = g(audio, "list", []) or []

    aud_items: List[AudioItem] = []
    if aud_use_folder:
        if aud_folder.exists():
            files = sorted([p for p in aud_folder.iterdir() if p.is_file()],
                           key=lambda p: p.name.lower())
            for p in files:
                if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
                    aud_items.append(AudioItem(path=p))
        else:
            log(f"WARNING: папка с аудио не найдена: {aud_folder}")
    else:
        for row in aud_list_raw:
            aud_items.append(AudioItem(
                path=Path(str(row.get("path", ""))),
                start=row.get("start", None),
                fade_in=row.get("fade_in", None),
                fade_out=row.get("fade_out", None),
                gain_db=row.get("gain_db", None),
            ))

    # Нормализация аудио
    norm_mode = str(g(audio_norm, "mode", "ebu_r128")).lower()
    norm_target = float(g(audio_norm, "target", -14.0))

    # Субтитры
    sub_enable = bool(g(subs, "enable", True))
    sub_mode = str(g(subs, "mode", "burn")).lower()         # "soft" | "burn"
    sub_encoding = str(g(subs, "encoding", "utf8")).lower()
    sub_select_strategy = str(g(subs, "select_strategy", "by_name_sequence")).lower()
    sub_allow_list = bool(g(subs, "allow_explicit_list", True))
    sub_file = g(subs, "file", "") or ""
    sub_file_path = Path(sub_file) if sub_file else None
    sub_folder = Path(g(subs, "folder", "./subs"))
    sub_list_raw = g(subs, "list", []) or []

    sub_items: List[SubItem] = []
    if sub_enable:
        if sub_allow_list and sub_list_raw:
            for row in sub_list_raw:
                sub_items.append(SubItem(path=Path(str(row.get("path", "")))))
        elif sub_file_path:
            sub_items.append(SubItem(path=sub_file_path))
        elif sub_folder.exists():
            files = sorted([p for p in sub_folder.iterdir() if p.is_file()],
                           key=lambda p: p.name.lower())
            for p in files:
                if p.suffix.lower() in {".srt", ".ass"}:
                    sub_items.append(SubItem(path=p))

    # Текст-оверлей
    text_enable = bool(g(textov, "enable", True))
    text_fontfile = str(g(textov, "fontfile", ""))
    text_use_folder = bool(g(textov, "use_folder", True))
    text_folder = Path(g(textov, "folder", "./texts"))
    text_order = str(g(textov, "order", "by_name")).lower()
    text_bind = bool(g(textov, "bind_to_images_by_order", True))
    text_list_raw = g(textov, "list", []) or []

    text_defaults = {
        "x": g(textov, "default_x", "(w-text_w)/2"),
        "y": g(textov, "default_y", "h*0.80"),
        "fontsize": int(g(textov, "default_fontsize", 36)),
        "line_spacing": int(g(textov, "default_line_spacing", 6)),
        "box": bool(g(textov, "default_box", True)),
        "boxcolor": g(textov, "default_boxcolor", "black@0.5"),
        "boxborderw": int(g(textov, "default_boxborderw", 10)),
        "fontcolor": g(textov, "default_fontcolor", "white"),
        "shadowcolor": g(textov, "default_shadowcolor", "black"),
        "shadowx": int(g(textov, "default_shadowx", 1)),
        "shadowy": int(g(textov, "default_shadowy", 1)),
    }

    text_items: List[TextItem] = []
    if text_use_folder:
        if text_folder.exists():
            files = sorted([p for p in text_folder.iterdir() if p.is_file()],
                           key=lambda p: p.name.lower())
            for p in files:
                if p.suffix.lower() == ".txt":
                    text_items.append(TextItem(path=p))
        else:
            log(f"INFO: папка с текстами не найдена: {text_folder} (оверлей будет отключён)")
    else:
        for row in text_list_raw:
            text_items.append(TextItem(
                path=Path(str(row.get("path", ""))),
                start=row.get("start", None),
                end=row.get("end", None),
                x=row.get("x", None),
                y=row.get("y", None),
                fontsize=row.get("fontsize", None),
                line_spacing=row.get("line_spacing", None),
                box=row.get("box", None),
                boxcolor=row.get("boxcolor", None),
                boxborderw=row.get("boxborderw", None),
                fontcolor=row.get("fontcolor", None),
                shadowcolor=row.get("shadowcolor", None),
                shadowx=row.get("shadowx", None),
                shadowy=row.get("shadowy", None),
            ))

    # Заглушки/безопасность
    ph_image_path = Path(ph_img.get("path", "")) if ph_img.get("path", "") else None
    ph_image_text = str(ph_img.get("text", ""))
    ph_audio_silence_enable = bool(ph_aud.get("enable", True))
    ph_audio_silence_db = float(ph_aud.get("loudness_db", -90.0))

    safety_stop = bool(safety.get("stop_on_missing", True))
    safety_fallback_image = Path(safety.get("fallback_image", "")) if safety.get("fallback_image", "") else None

    # Прочее
    timing_snap = bool(timing.get("snap_to_frames", True))
    timing_offset = float(timing.get("global_offset", 0.0))
    log_level = str(logging_cfg.get("level", "INFO")).upper()
    log_to_file = bool(logging_cfg.get("to_file", False))

    return Config(
        out_filename=out_filename, overwrite=overwrite, sidecar_timeline=sidecar,
        resolution=resolution, fps=fps, bg_mode=bg_mode, bg_color=bg_color, default_image_duration=default_img_dur,
        tr_type=tr_type, tr_duration=tr_duration,
        img_use_folder=img_use_folder, img_folder=img_folder, img_order=img_order, img_list=img_items,
        aud_mode=aud_mode, aud_use_folder=aud_use_folder, aud_folder=aud_folder, aud_order=aud_order, aud_list=aud_items,
        norm_mode=norm_mode, norm_target=norm_target,
        sub_enable=sub_enable, sub_mode=sub_mode, sub_encoding=sub_encoding, sub_select_strategy=sub_select_strategy,
        sub_allow_list=sub_allow_list, sub_file=sub_file_path, sub_folder=sub_folder, sub_list=sub_items,
        sub_style_preset=str(subs_style.get("preset", "default")),
        text_enable=text_enable, text_fontfile=text_fontfile, text_use_folder=text_use_folder,
        text_folder=text_folder, text_order=text_order, text_bind_to_images=text_bind,
        text_defaults=text_defaults, text_list=text_items,
        ph_image_path=ph_image_path, ph_image_text=ph_image_text,
        ph_audio_silence_enable=ph_audio_silence_enable, ph_audio_silence_db=ph_audio_silence_db,
        safety_stop_on_missing=safety_stop, safety_fallback_image=safety_fallback_image,
        timing_snap=timing_snap, timing_offset=timing_offset,
        log_level=log_level, log_to_file=log_to_file,
    )

# ====================== ТАЙМЛАЙНЫ ======================

def resolution_to_wh(res: str) -> Tuple[int, int]:
    res = res.lower()
    if res == "720p": return 1280, 720
    if res == "4k":   return 3840, 2160
    return 1920, 1080

def probe_duration_seconds(path: Path) -> float:
    try:
        out = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration","-of","json",str(path)],
            capture_output=True, text=True
        )
        dur = float(json.loads(out.stdout or "{}").get("format",{}).get("duration",0.0))
        return max(dur,0.0)
    except Exception:
        return 0.0

def build_images_timeline(cfg: Config) -> List[Tuple[ImageItem,float,float]]:
    tl=[]; t=0.0
    for it in cfg.img_list:
        if not it.path.exists():
            if cfg.safety_stop_on_missing: die(f"Изображение не найдено: {it.path}")
            else: log(f"WARNING: изображение отсутствует: {it.path} — пропускаем."); continue
        dur = it.duration if (it.duration and it.duration>0) else cfg.default_image_duration
        start = it.start if it.start is not None else t
        end = start + dur
        tl.append((it,start,end))
        if (it.transition and it.transition in {"crossfade","dip"}) or cfg.tr_type in {"crossfade","dip"}:
            t = max(0.0, end - cfg.tr_duration)
        else:
            t = end
    return tl

def build_audio_timeline_sequence(cfg: Config) -> List[Tuple[AudioItem,float,float]]:
    tl=[]; t=0.0
    for it in cfg.aud_list:
        if not it.path.exists():
            if cfg.safety_stop_on_missing: die(f"Аудио не найдено: {it.path}")
            else: log(f"WARNING: аудио отсутствует: {it.path} — пропускаем."); continue
        dur=probe_duration_seconds(it.path)
        start = it.start if it.start is not None else t
        end = start + (dur if dur>0 else 0)
        tl.append((it,start,end)); t=end
    return tl

def build_audio_timeline_mix(cfg: Config) -> List[Tuple[AudioItem,float,float]]:
    tl=[]
    for it in cfg.aud_list:
        if not it.path.exists():
            if cfg.safety_stop_on_missing: die(f"Аудио не найдено: {it.path}")
            else: log(f"WARNING: аудио отсутствует: {it.path} — пропускаем."); continue
        dur=probe_duration_seconds(it.path)
        start = it.start if it.start is not None else 0.0
        end = start + (dur if dur>0 else 0)
        tl.append((it,start,end))
    tl.sort(key=lambda x: x[1])
    return tl

def pair_texts_to_images(cfg: Config,
                         img_tl: List[Tuple[ImageItem,float,float]]
                         ) -> List[Tuple[TextItem,float,float,dict]]:
    """Сопоставляем .txt файлы кадрам (или используем их собственные start/end)."""
    result=[]
    if not cfg.text_enable or not cfg.text_list: return result
    d=cfg.text_defaults
    if cfg.text_bind_to_images:
        n=min(len(cfg.text_list),len(img_tl))
        for i in range(n):
            txt=cfg.text_list[i]; s=img_tl[i][1]; e=img_tl[i][2]
            if txt.start is not None: s=txt.start
            if txt.end   is not None: e=txt.end
            style=dict(
                x=txt.x or d["x"], y=txt.y or d["y"], fontsize=txt.fontsize or d["fontsize"],
                line_spacing=txt.line_spacing or d["line_spacing"],
                box=d["box"] if txt.box is None else txt.box, boxcolor=txt.boxcolor or d["boxcolor"],
                boxborderw=txt.boxborderw or d["boxborderw"], fontcolor=txt.fontcolor or d["fontcolor"],
                shadowcolor=txt.shadowcolor or d["shadowcolor"], shadowx=txt.shadowx or d["shadowx"],
                shadowy=txt.shadowy or d["shadowy"],
            )
            result.append((txt,s,e,style))
    else:
        for txt in cfg.text_list:
            if txt.start is None or txt.end is None:
                log(f"INFO: текст {txt.path} пропущен (нет start/end при bind_to_images_by_order=false)"); continue
            style=dict(
                x=txt.x or d["x"], y=txt.y or d["y"], fontsize=txt.fontsize or d["fontsize"],
                line_spacing=txt.line_spacing or d["line_spacing"],
                box=d["box"] if txt.box is None else txt.box, boxcolor=txt.boxcolor or d["boxcolor"],
                boxborderw=txt.boxborderw or d["boxborderw"], fontcolor=txt.fontcolor or d["fontcolor"],
                shadowcolor=txt.shadowcolor or d["shadowcolor"], shadowx=txt.shadowx or d["shadowx"],
                shadowy=txt.shadowy or d["shadowy"],
            )
            result.append((txt,txt.start,txt.end,style))
    return result

# ====================== ПОМОЩНИК ДЛЯ АУДИО-ФИЛЬТРОВ ======================

def build_audio_chain(lin: str, filters: list[str], lout: str, delay_ms: int | None = None) -> str:
    """
    Собирает корректную цепочку для ffmpeg БЕЗ лишней запятой после [in]:
      [in]filter1,filter2[,adelay=...][out]
    Если фильтров нет — подставляет 'anull' (пустой фильтр недопустим).
    """
    parts: list[str] = []
    if filters:
        parts.append(filters[0])
        if len(filters) > 1:
            parts.append(",".join(filters[1:]))
    if delay_ms is not None and delay_ms > 0:
        parts.append(f"adelay={delay_ms}:all=1")
    body = ",".join([p for p in parts if p])
    if not body:
        body = "anull"
    return f"{lin}{body}{lout}"

# ====================== СБОРКА КОМАНДЫ FFMPEG ======================

def build_ffmpeg_command(cfg: Config,
                         img_tl: List[Tuple[ImageItem,float,float]],
                         aud_tl_seq: List[Tuple[AudioItem,float,float]],
                         aud_tl_mix: List[Tuple[AudioItem,float,float]],
                         text_tl: List[Tuple[TextItem,float,float,dict]]) -> List[str]:
    W,H = resolution_to_wh(cfg.resolution); fps=cfg.fps
    args=["ffmpeg","-y" if cfg.overwrite else "-n"]
    fc=[]; v_labels=[]; bg=cfg.bg_color

    # Входы: изображения
    for (it,s,e) in img_tl:
        dur=max(e-s,0.001); args+=["-loop","1","-t",f"{dur:.3f}","-i",str(it.path)]
    # Входы: аудио
    aud_source = aud_tl_mix if cfg.aud_mode=="mix" else aud_tl_seq
    for (it,s,e) in aud_source:
        args+=["-i",str(it.path)]

    # Подготовка каждого видеосегмента
    for i,(it,s,e) in enumerate(img_tl):
        src=f"[{i}:v]"; out=f"[v{i}]"
        if cfg.bg_mode in {"contain","fit","pad"}:
            chain=(f"{src}"
                   f"scale=w={W}:h={H}:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},"
                   f"fps={fps},format=yuv420p{out}")
        elif cfg.bg_mode=="cover":
            chain=(f"{src}"
                   f"scale=w={W}:h={H}:force_original_aspect_ratio=increase,"
                   f"crop={W}:{H},fps={fps},format=yuv420p{out}")
        else:
            chain=(f"{src}"
                   f"scale=w={W}:h={H}:force_original_aspect_ratio=decrease,"
                   f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},"
                   f"fps={fps},format=yuv420p{out}")
        fc.append(chain); v_labels.append(out)

    # Склейка видео
    if not v_labels:
        total_audio = sum(max(e-s,0.0) for _,s,e in aud_source); total_dur = total_audio if total_audio>0 else 5.0
        fc.append(f"color=color={bg}:size={W}x{H}:rate={fps},format=yuv420p,trim=duration={total_dur}[vbg]"); v_final="[vbg]"
    else:
        if len(v_labels)==1:
            v_final=v_labels[0]
        elif cfg.tr_type in {"crossfade","dip"} and cfg.tr_duration>0:
            prev=v_labels[0]
            for i in range(1,len(v_labels)):
                cur=v_labels[i]; out=f"[x{i}]"; extra=":fadeblack=1" if cfg.tr_type=="dip" else ""
                seg_prev = (img_tl[i-1][2]-img_tl[i-1][1]); offset=max(0.0, seg_prev - cfg.tr_duration)
                fc.append(f"{prev}{cur}xfade=transition=fade:duration={cfg.tr_duration:.3f}:offset={offset:.3f}{extra}{out}")
                prev=out
            v_final=prev
        else:
            fc.append("".join(v_labels)+f"concat=n={len(v_labels)}:v=1:a=0[vcat]"); v_final="[vcat]"

    # Аудио
    a_final=None; base=len(img_tl)
    if aud_source:
        if cfg.aud_mode=="sequence":
            a_labels=[]
            for i,(it,s,e) in enumerate(aud_tl_seq):
                lin=f"[{base+i}:a]"; lout=f"[a{i}]"; flt=[]
                if it.fade_in and it.fade_in>0:   flt.append(f"afade=t=in:st=0:d={it.fade_in:.3f}")
                if it.fade_out and it.fade_out>0: flt.append(f"afade=t=out:st=0:d={it.fade_out:.3f}")
                if it.gain_db and abs(it.gain_db)>1e-6: flt.append(f"volume={it.gain_db:.3f}dB")
                if cfg.norm_mode=="ebu_r128": flt.append(f"loudnorm=I={cfg.norm_target:.1f}:TP=-1.0:LRA=11.0:print_format=summary")
                fc.append(build_audio_chain(lin, flt, lout)); a_labels.append(lout)
            if len(a_labels)==1: a_final=a_labels[0]
            else: fc.append("".join(a_labels)+f"concat=n={len(a_labels)}:v=0:a=1[acat]"); a_final="[acat]"
        else:
            a_labels=[]
            for i,(it,s,e) in enumerate(aud_tl_mix):
                lin=f"[{base+i}:a]"; lout=f"[am{i}]"; flt=[]
                if it.fade_in and it.fade_in>0:   flt.append(f"afade=t=in:st=0:d={it.fade_in:.3f}")
                if it.fade_out and it.fade_out>0: flt.append(f"afade=t=out:st=0:d={it.fade_out:.3f}")
                if it.gain_db and abs(it.gain_db)>1e-6: flt.append(f"volume={it.gain_db:.3f}dB")
                if cfg.norm_mode=="ebu_r128": flt.append(f"loudnorm=I={cfg.norm_target:.1f}:TP=-1.0:LRA=11.0:print_format=summary")
                delay_ms=int(max(0.0,s)*1000)
                fc.append(build_audio_chain(lin, flt, lout, delay_ms=delay_ms)); a_labels.append(lout)
            fc.append("".join(a_labels)+f"amix=inputs={len(a_labels)}:duration=longest:dropout_transition=0[mixout]"); a_final="[mixout]"

    # Текст-оверлей (накладываем ДО прожига субтитров)
    map_video=v_final
    if cfg.text_enable and text_tl:
        for i,(txt,s,e,st) in enumerate(text_tl):
            out=f"[vt{i}]"
            # Читаем текст из файла (UTF-8). Если нельзя — пропускаем.
            try:
                content = txt.path.read_text(encoding="utf-8")
            except Exception as ex:
                log(f"WARNING: не удалось прочитать текст {txt.path}: {ex}; пропускаем")
                content = ""
            if not content.strip():
                fc.append(f"{map_video}null{out}")
                map_video = out
                continue

            esc = escape_drawtext_text(content)
            enable_expr = f"between(t,{s:.6f},{e:.6f})"
            params=[
                f"text='{esc}'",
                f"enable='{enable_expr}'",
                f"x={st['x']}",
                f"y={st['y']}",
                f"fontsize={st['fontsize']}",
                f"line_spacing={st['line_spacing']}",
                f"fontcolor={st['fontcolor']}",
                f"shadowcolor={st['shadowcolor']}",
                f"shadowx={st['shadowx']}",
                f"shadowy={st['shadowy']}",
            ]
            if st["box"]:
                params += [f"box=1", f"boxcolor={st['boxcolor']}", f"boxborderw={st['boxborderw']}"]
            if cfg.text_fontfile:
                fontfile_path = Path(cfg.text_fontfile).as_posix()
                # fontfile допускает обычный POSIX-путь; пробелы/двоеточия тут не мешают
                params.append(f"fontfile='{fontfile_path}'")

            fc.append(f"{map_video}drawtext={':'.join(params)}{out}")
            map_video=out

    # Субтитры (с учётом sub_enable)
    subtitle_soft=False
    if cfg.sub_enable and cfg.sub_list:
        if cfg.sub_mode=="soft":
            args+=["-i", str(cfg.sub_list[0].path)]; subtitle_soft=True
        elif cfg.sub_mode=="burn":
            for i,su in enumerate(cfg.sub_list):
                out=f"[vb{i}]"; fc.append(f"{map_video}subtitles='{su.path.as_posix()}'{out}"); map_video=out

    # filter_complex
    if fc: args+=["-filter_complex",";".join(fc)]

    # map + кодеки (YouTube-friendly)
    args+=["-map",map_video]
    if a_final: args+=["-map",a_final]
    args+=[
        "-c:v","libx264","-preset","medium","-profile:v","high","-pix_fmt","yuv420p","-r",str(cfg.fps),
        "-movflags","+faststart","-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709"
    ]
    if a_final: args+=["-c:a","aac","-b:a","192k"]
    if subtitle_soft: args+=["-c:s","mov_text"]
    args+=[str(cfg.out_filename)]
    return args

# ====================== MAIN ======================

def main() -> None:
    check_ffmpeg_available()

    parser = argparse.ArgumentParser(
        description="Видео из картинок + аудио (sequence/mix) + субтитры + текст-оверлей. Конфиг по умолчанию берётся рядом со скриптом."
    )
    parser.add_argument("--config", default=str(default_config_path()),
                        help="Путь к config.toml. Если не указан — используем файл рядом со скриптом.")
    parser.add_argument("--dry-run", action="store_true", help="Показать таймлайн (без рендера)")
    parser.add_argument("--verbose", action="store_true", help="Показать собранную команду ffmpeg")
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve()
    log(f"Используем конфиг: {cfg_path}")
    cfg = load_config(cfg_path)

    if cfg.text_enable and not cfg.text_fontfile and os.name=="nt":
        log("INFO: text_overlay.fontfile не указан. На Windows drawtext часто требует явный путь к .ttf/.otf (например, C:/Windows/Fonts/arial.ttf).")
    if not cfg.img_list: log("WARNING: список изображений пуст — будет однотонный фон.")
    if not cfg.aud_list: log("WARNING: список аудио пуст — ролик будет без звука.")

    # таймлайны
    img_tl = build_images_timeline(cfg)
    aud_tl_seq = build_audio_timeline_sequence(cfg) if cfg.aud_mode=="sequence" else []
    aud_tl_mix = build_audio_timeline_mix(cfg) if cfg.aud_mode=="mix" else []
    text_tl = pair_texts_to_images(cfg, img_tl) if (cfg.text_enable and cfg.text_list) else []

    if args.dry_run:
        log("=== DRY RUN: ИЗОБРАЖЕНИЯ ===")
        for (it,s,e) in img_tl:
            log(f"{it.path.name:30} start={s:8.3f} end={e:8.3f} dur={e-s:6.3f} tr={it.transition or cfg.tr_type}")
        if cfg.aud_mode=="sequence":
            log("=== DRY RUN: АУДИО (sequence) ===")
            for (it,s,e) in aud_tl_seq:
                log(f"{it.path.name:30} start={s:8.3f} end={e:8.3f} dur={e-s:6.3f}")
        else:
            log("=== DRY RUN: АУДИО (mix) ===")
            for (it,s,e) in aud_tl_mix:
                log(f"{it.path.name:30} start={s:8.3f} end={e:8.3f} dur={e-s:6.3f}")
        if cfg.text_enable:
            log("=== DRY RUN: ТЕКСТОВЫЕ ОВЕРЛЕИ ===")
            if not text_tl:
                log("нет валидных текстовых интервалов (папка пуста или файлы не совпали по количеству)")
            for (t,s,e,st) in text_tl:
                log(f"{t.path.name:30} start={s:8.3f} end={e:8.3f} x={st['x']} y={st['y']} fontsize={st['fontsize']}")
        if cfg.sidecar_timeline:
            sidecar={
                "video":{"resolution":cfg.resolution,"fps":cfg.fps},
                "images":[{"path":str(it.path),"start":s,"end":e} for (it,s,e) in img_tl],
                "audio_mode":cfg.aud_mode,
                "audio":[{"path":str(it.path),"start":s,"end":e} for (it,s,e) in (aud_tl_mix if cfg.aud_mode=="mix" else aud_tl_seq)],
                "text":[{"path":str(t.path),"start":s,"end":e} for (t,s,e,_) in text_tl],
                "subs":[str(s.path) for s in cfg.sub_list] if cfg.sub_enable else [],
            }
            Path(cfg.out_filename).with_suffix(".timeline.json").write_text(
                json.dumps(sidecar,ensure_ascii=False,indent=2),encoding="utf-8"
            )
            log(f"Сохранён таймлайн: {Path(cfg.out_filename).with_suffix('.timeline.json')}")
        log("DRY RUN завершён."); return

    cmd = build_ffmpeg_command(cfg, img_tl, aud_tl_seq, aud_tl_mix, text_tl)
    if args.verbose: log("FFMPEG CMD:\n"+" ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc!=0: die(f"ffmpeg завершился с кодом {rc}. Проверьте входные файлы/пути/шрифты/саб-файлы.")

    if cfg.sidecar_timeline:
        sidecar={
            "video":{"resolution":cfg.resolution,"fps":cfg.fps},
            "images":[{"path":str(it.path),"start":s,"end":e} for (it,s,e) in img_tl],
            "audio_mode":cfg.aud_mode,
            "audio":[{"path":str(it.path),"start":s,"end":e} for (it,s,e) in (aud_tl_mix if cfg.aud_mode=="mix" else aud_tl_seq)],
            "text":[{"path":str(t.path),"start":s,"end":e} for (t,s,e,_) in text_tl],
            "subs":[str(s.path) for s in cfg.sub_list] if cfg.sub_enable else [],
        }
        Path(cfg.out_filename).with_suffix(".timeline.json").write_text(
            json.dumps(sidecar,ensure_ascii=False,indent=2),encoding="utf-8"
        )
        log(f"Сохранён таймлайн: {Path(cfg.out_filename).with_suffix('.timeline.json')}")
    log(f"Готово: {cfg.out_filename}")

if __name__=="__main__":
    main()
