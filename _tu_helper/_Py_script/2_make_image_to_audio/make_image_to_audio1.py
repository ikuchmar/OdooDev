#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание пустых (или фоновых) изображений под каждый аудиофайл.
- Настройки берутся из config.toml, лежащего рядом со скриптом.
- Запуск без параметров: python make_image_from_audio.py
- Требуется Python 3.11+ (для tomllib) и Pillow (PIL) для работы с изображениями.

Если Pillow не установлен:
    pip install Pillow

Автор: вы :)
"""

from __future__ import annotations

import os
import sys
import re
import io
import math
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

# --- Чтение TOML ---
# tomllib — стандартный модуль в Python 3.11+
try:
    import tomllib  # type: ignore
except Exception as e:
    print("❌ Не удалось импортировать tomllib (нужен Python 3.11+). Обновите Python.")
    sys.exit(1)

# --- Изображения (Pillow) ---
try:
    from PIL import Image, ImageDraw
except Exception as e:
    print("❌ Не установлен Pillow (PIL). Установите: pip install Pillow")
    sys.exit(1)

# --- Пулы потоков (опционально) ---
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# УТИЛИТЫ
# =========================

def script_dir() -> Path:
    """Каталог, где лежит скрипт."""
    return Path(__file__).resolve().parent

def load_config() -> Dict[str, Any]:
    """
    Ищем config.toml рядом со скриптом и парсим его.
    Формат: TOML.
    """
    cfg_path = script_dir() / "config.toml"
    if not cfg_path.exists():
        print(f"❌ Не найден файл настроек: {cfg_path}")
        sys.exit(1)
    try:
        with open(cfg_path, "rb") as f:
            data = tomllib.load(f)
        return data
    except Exception as e:
        print(f"❌ Ошибка чтения {cfg_path}:\n{e}")
        sys.exit(1)

def log_print(msg: str, log_fp: Optional[io.TextIOBase]):
    """Печать в консоль и (опц.) в файл лога."""
    print(msg)
    if log_fp:
        log_fp.write(msg + "\n")
        log_fp.flush()

def is_audio_file(path: Path, audio_exts: List[str]) -> bool:
    """Проверка расширения аудиофайла (без учёта регистра)."""
    ext = path.suffix.lower()
    return ext in [e.lower() for e in audio_exts]

def ensure_dir(p: Path):
    """Создать директорию (включая родителей)."""
    p.mkdir(parents=True, exist_ok=True)

def safe_name_with_suffix(target: Path) -> Path:
    """
    Возвращает путь с уникальным суффиксом _1, _2, ... чтобы не перезаписывать.
    """
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    parent = target.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def hex_to_rgba(color_hex: str) -> Tuple[int, int, int, int]:
    """
    Преобразует #RRGGBB или #RRGGBBAA в кортеж RGBA.
    """
    s = color_hex.strip()
    if not s.startswith("#"):
        raise ValueError("Цвет должен быть в формате #RRGGBB или #RRGGBBAA")
    s = s[1:]
    if len(s) == 6:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = 255
    elif len(s) == 8:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        a = int(s[6:8], 16)
    else:
        raise ValueError("Неверная длина HEX-строки цвета")
    return (r, g, b, a)

def make_solid_image(w: int, h: int, rgba: Tuple[int, int, int, int]) -> Image.Image:
    """Создать однотонное изображение RGBA."""
    return Image.new("RGBA", (w, h), rgba)

def make_gradient_image(w: int, h: int, rgba_from: Tuple[int,int,int,int], rgba_to: Tuple[int,int,int,int], direction: str) -> Image.Image:
    """
    Создать простейший линейный градиент (вертикальный или горизонтальный).
    """
    base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)

    if direction.lower() == "horizontal":
        for x in range(w):
            t = x / max(1, (w - 1))
            r = int(rgba_from[0] + (rgba_to[0] - rgba_from[0]) * t)
            g = int(rgba_from[1] + (rgba_to[1] - rgba_from[1]) * t)
            b = int(rgba_from[2] + (rgba_to[2] - rgba_from[2]) * t)
            a = int(rgba_from[3] + (rgba_to[3] - rgba_from[3]) * t)
            draw.line([(x, 0), (x, h)], fill=(r, g, b, a))
    else:
        # vertical by default
        for y in range(h):
            t = y / max(1, (h - 1))
            r = int(rgba_from[0] + (rgba_to[0] - rgba_from[0]) * t)
            g = int(rgba_from[1] + (rgba_to[1] - rgba_from[1]) * t)
            b = int(rgba_from[2] + (rgba_to[2] - rgba_from[2]) * t)
            a = int(rgba_from[3] + (rgba_to[3] - rgba_from[3]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b, a))

    return base

def fit_background(img: Image.Image, canvas_w: int, canvas_h: int, mode: str) -> Image.Image:
    """
    Встраивание фоновой картинки на холст:
      - contain: вписать без обрезки, добавить поля (letterbox)
      - cover:   заполнить всё, обрезая лишнее
      - stretch: растянуть до точного размера
    """
    mode = (mode or "contain").lower()
    if mode == "stretch":
        return img.resize((canvas_w, canvas_h), Image.LANCZOS)

    # вычисление масштаба
    iw, ih = img.size
    if iw == 0 or ih == 0:
        return Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    scale_w = canvas_w / iw
    scale_h = canvas_h / ih

    if mode == "cover":
        scale = max(scale_w, scale_h)
    else:  # contain
        scale = min(scale_w, scale_h)

    new_w = max(1, int(round(iw * scale)))
    new_h = max(1, int(round(ih * scale)))
    resized = img.resize((new_w, new_h), Image.LANCZOS)

    # Помещаем по центру на прозрачный холст и вернём
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    off_x = (canvas_w - new_w) // 2
    off_y = (canvas_h - new_h) // 2
    canvas.paste(resized, (off_x, off_y))
    return canvas

def make_background(cfg_img: Dict[str, Any]) -> Image.Image:
    """
    Сборка фона согласно конфигу image.background.
    Возвращает RGBA-изображение нужного размера.
    """
    w = int(cfg_img.get("width", 1920))
    h = int(cfg_img.get("height", 1080))
    bg = cfg_img.get("background", {}) or {}
    bg_type = (bg.get("type") or "color").lower()

    if bg_type == "color":
        rgba = hex_to_rgba(str(bg.get("value", "#000000")))
        return make_solid_image(w, h, rgba)

    elif bg_type == "gradient":
        c_from = hex_to_rgba(str(bg.get("from", "#000000")))
        c_to   = hex_to_rgba(str(bg.get("to", "#FFFFFF")))
        direction = str(bg.get("direction", "vertical"))
        return make_gradient_image(w, h, c_from, c_to, direction)

    elif bg_type == "image":
        path = bg.get("path")
        fit = str(bg.get("fit", "contain"))
        if not path:
            raise ValueError("Для background.type='image' требуется параметр 'path'")
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Фоновая картинка не найдена: {p}")
        img = Image.open(p).convert("RGBA")
        return fit_background(img, w, h, fit)

    else:
        raise ValueError(f"Неизвестный тип фона: {bg_type}")

def collect_audio_files(cfg: Dict[str, Any], log_fp: Optional[io.TextIOBase]) -> List[Path]:
    """
    Собрать список аудиофайлов из input_dir (+recursive) и input_files.
    Возвращается уникальный список Path.
    """
    audio_exts = cfg.get("audio_exts") or [".mp3", ".wav", ".m4a", ".flac"]
    input_dir = (cfg.get("input_dir") or "").strip()
    recursive = bool(cfg.get("recursive", True))
    input_files = cfg.get("input_files") or []

    files: List[Path] = []

    # Из папки
    if input_dir:
        base = Path(input_dir)
        if base.exists() and base.is_dir():
            pattern = "**/*" if recursive else "*"
            for p in base.glob(pattern):
                if p.is_file() and is_audio_file(p, audio_exts):
                    files.append(p.resolve())
        else:
            log_print(f"⚠️  input_dir не существует или не папка: {base}", log_fp)

    # Из списка
    for f in input_files:
        p = Path(f)
        if p.exists() and p.is_file():
            if is_audio_file(p, audio_exts):
                files.append(p.resolve())
            else:
                log_print(f"⚠️  В списке input_files встречен не-аудио файл: {p}", log_fp)
        else:
            log_print(f"⚠️  В списке input_files путь не найден: {p}", log_fp)

    # Уникализация + сортировка для стабильности
    uniq = sorted(set(files))
    log_print(f"Найдено аудиофайлов: {len(uniq)}", log_fp)
    return uniq

def compute_output_path(
    in_file: Path,
    cfg: Dict[str, Any],
    image_format: str
) -> Path:
    """
    Определить путь сохранения итогового изображения для аудио-файла in_file.
    Учитывает output_dir (или рядом), mirror_subdirs и формат.
    """
    out_dir_cfg = (cfg.get("output_dir") or "").strip()
    mirror = bool(cfg.get("mirror_subdirs", True))

    if not out_dir_cfg:
        # Сохраняем рядом с аудио
        target_dir = in_file.parent
    else:
        base_out = Path(out_dir_cfg)
        if not mirror:
            target_dir = base_out
        else:
            # Повторить структуру подпапок относительно input_dir (если задан)
            input_dir = (cfg.get("input_dir") or "").strip()
            if input_dir:
                try:
                    rel = in_file.parent.resolve().relative_to(Path(input_dir).resolve())
                    target_dir = base_out / rel
                except Exception:
                    # Если не удалось вычислить относительный путь — складываем в корень output_dir
                    target_dir = base_out
            else:
                target_dir = base_out

    ensure_dir(target_dir)
    new_name = f"{in_file.stem}.{image_format.lower()}"
    return target_dir / new_name

def save_image(img: Image.Image, path: Path, image_format: str, jpeg_quality: int, conflicts: str, dry_run: bool, log_fp: Optional[io.TextIOBase]):
    """
    Сохранение с учётом политики конфликтов.
    """
    image_format = image_format.upper()
    conflicts = (conflicts or "skip").lower()

    target = path
    if target.exists():
        if conflicts == "skip":
            log_print(f"⏭️  Уже существует, пропускаем: {target}", log_fp)
            return
        elif conflicts == "rename":
            target = safe_name_with_suffix(target)
        elif conflicts == "overwrite":
            pass
        else:
            log_print(f"⚠️  Неизвестная политика conflicts='{conflicts}', считаем как 'skip'", log_fp)
            return

    if dry_run:
        log_print(f"[dry-run] Сохранили бы: {target}", log_fp)
        return

    # Конвертация для форматов без альфы
    save_kwargs = {}
    to_save = img
    if image_format in ("JPG", "JPEG", "WEBP"):
        save_kwargs["quality"] = max(1, min(95, int(jpeg_quality)))
        if to_save.mode not in ("RGB", "L"):
            # удаляем альфу на белый фон (или чёрный — на ваше усмотрение)
            bg = Image.new("RGB", to_save.size, (255, 255, 255))
            bg.paste(to_save, mask=to_save.split()[-1] if "A" in to_save.getbands() else None)
            to_save = bg

    to_save.save(target, format=image_format, **save_kwargs)
    log_print(f"💾 Сохранено: {target}", log_fp)

@dataclass
class Job:
    in_file: Path
    out_file: Path

def process_one(job: Job, cfg_img: Dict[str, Any], conflicts: str, dry_run: bool, log_fp: Optional[io.TextIOBase]):
    """
    Обработка одного аудиофайла: сгенерировать фон и сохранить.
    """
    try:
        img = make_background(cfg_img)
        save_image(
            img=img,
            path=job.out_file,
            image_format=str(cfg_img.get("format", "png")),
            jpeg_quality=int(cfg_img.get("jpeg_quality", 90)),
            conflicts=conflicts,
            dry_run=dry_run,
            log_fp=log_fp
        )
        return True, None
    except Exception as e:
        tb = traceback.format_exc()
        log_print(f"❌ Ошибка для {job.in_file}:\n{tb}", log_fp)
        return False, e

def main():
    cfg = load_config()

    # Настройки верхнего уровня
    dry_run = bool(cfg.get("dry_run", False))
    conflicts = str(cfg.get("conflicts", "skip"))
    workers = int(cfg.get("workers", 0))
    log_file = (cfg.get("log_file") or "").strip()

    # Открываем лог-файл, если задан
    log_fp: Optional[io.TextIOBase] = None
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            log_fp = open(log_file, "a", encoding="utf-8")
        except Exception as e:
            print(f"⚠️  Не удалось открыть лог-файл '{log_file}': {e}")

    # Блок image
    cfg_img = cfg.get("image") or {}
    cfg_img.setdefault("width", 1920)
    cfg_img.setdefault("height", 1080)
    cfg_img.setdefault("format", "png")
    cfg_img.setdefault("jpeg_quality", 90)
    if "background" not in cfg_img:
        cfg_img["background"] = {"type": "color", "value": "#000000"}

    # Сбор входных аудиофайлов
    files = collect_audio_files(cfg, log_fp)
    if not files:
        log_print("ℹ️  Аудиофайлов не найдено — делать нечего.", log_fp)
        if log_fp:
            log_fp.close()
        return

    # Формирование задач
    image_format = str(cfg_img.get("format", "png"))
    jobs: List[Job] = []
    for f in files:
        out = compute_output_path(f, cfg, image_format=image_format)
        jobs.append(Job(in_file=f, out_file=out))

    # Информация о запуске
    log_print(f"Старт. Всего задач: {len(jobs)} | dry_run={dry_run} | workers={workers}", log_fp)

    # Обработка
    ok = 0
    fail = 0

    if workers and workers > 1:
        # Параллельно в пуле потоков
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {
                ex.submit(process_one, job, cfg_img, conflicts, dry_run, log_fp): job
                for job in jobs
            }
            for fut in as_completed(futures):
                success, err = fut.result()
                if success:
                    ok += 1
                else:
                    fail += 1
    else:
        # Последовательно
        for job in jobs:
            success, err = process_one(job, cfg_img, conflicts, dry_run, log_fp)
            if success:
                ok += 1
            else:
                fail += 1

    # Итог
    log_print(f"Готово. Успешно: {ok} | Ошибок: {fail}", log_fp)
    if log_fp:
        log_fp.close()

if __name__ == "__main__":
    main()
