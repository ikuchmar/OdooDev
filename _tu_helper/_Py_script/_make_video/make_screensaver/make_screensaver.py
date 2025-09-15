#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Склейка видео из картинок с индивидуальной длительностью.
Запуск: просто запустите скрипт без параметров. Все настройки — в config.toml рядом со скриптом.

Требования:
- Python 3.11+ (для встроенного tomllib). Если Python 3.10 и ниже — установите tomli и раскомментируйте импорт.
- Установленный FFmpeg в PATH (проверьте: ffmpeg -version).

Автор: подготовлено для проекта "Изучение Английского".
"""

from __future__ import annotations
import os
import sys
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

# Python 3.11+: tomllib встроен
try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:
    # Для Python <=3.10 можно использовать tomli:
    # pip install tomli
    import tomli as tomllib  # type: ignore[no-redef]


# ---------------------------
# Утилиты логирования
# ---------------------------
def info(msg: str) -> None:
    print(f"[INFO] {msg}", flush=True)

def warn(msg: str) -> None:
    print(f"[WARN] {msg}", flush=True)

def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)


# ---------------------------
# Загрузка конфига
# ---------------------------
def load_config(cfg_path: Path) -> dict:
    if not cfg_path.exists():
        err(f"Не найден файл настроек: {cfg_path}")
        sys.exit(2)
    with cfg_path.open("rb") as f:
        data = tomllib.load(f)
    return data


# ---------------------------
# Валидация и подготовка
# ---------------------------
def validate_and_prepare(cfg: dict, base_dir: Path) -> tuple[dict, list[dict]]:
    # Параметры с разумными дефолтами
    video = cfg.get("video", {})
    images = cfg.get("images", [])

    if not isinstance(images, list) or not images:
        err("В config.toml отсутствует или пуст раздел [[images]].")
        sys.exit(2)

    # Значения по умолчанию
    defaults = {
        "output": "output.mp4",
        "width": 1920,
        "height": 1080,
        "background": "#000000",
        "fps": 30,
        "codec": "libx264",
        "crf": 18,
        "preset": "medium",
        "pixel_format": "yuv420p",
        "audio": "",
        "audio_offset": 0.0,
        "shortest": True,
        "temp_dir": "_temp",
        "list_filename": "concat_list.txt",
        "log_level": "info",
        "continue_on_error": False,
    }
    for k, v in defaults.items():
        video.setdefault(k, v)

    # Привести пути
    output_path = Path(video["output"])
    if not output_path.is_absolute():
        output_path = (base_dir / output_path).resolve()
    video["output"] = str(output_path)

    # Временная папка
    temp_dir = Path(video["temp_dir"])
    if not temp_dir.is_absolute():
        temp_dir = (base_dir / temp_dir).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    video["temp_dir"] = str(temp_dir)

    # Список изображений
    prepared_images: list[dict] = []
    had_errors = False

    for idx, item in enumerate(images, start=1):
        if not isinstance(item, dict):
            err(f"images[{idx}] не объект.")
            had_errors = True
            continue
        path = item.get("path")
        duration = item.get("duration")

        if not path or not isinstance(path, str):
            err(f"images[{idx}] отсутствует строковый параметр 'path'.")
            had_errors = True
            continue
        if not isinstance(duration, (int, float)) or duration <= 0:
            err(f"images[{idx}] некорректная 'duration' (должна быть > 0).")
            had_errors = True
            continue

        p = Path(path)
        if not p.is_absolute():
            warn(f"images[{idx}] путь не абсолютный: {p}. Рекомендуется указывать полный путь.")
            # Разрешим относительный — относительно config.py/скрипта:
            p = (base_dir / p).resolve()

        if not p.exists():
            msg = f"images[{idx}] файл не найден: {p}"
            if video["continue_on_error"]:
                warn(msg + " (будет пропущен)")
                continue
            else:
                err(msg)
                had_errors = True
                continue

        prepared_images.append({"path": str(p), "duration": float(duration)})

    if not prepared_images:
        err("После валидации не осталось ни одного изображения.")
        sys.exit(2)

    if had_errors and not video["continue_on_error"]:
        err("Обнаружены ошибки. Прерывание (continue_on_error=false).")
        sys.exit(2)

    return video, prepared_images


# ---------------------------
# Генерация concat-листа
# ---------------------------
def write_concat_list(temp_dir: Path, list_filename: str, items: list[dict]) -> Path:
    concat_path = temp_dir / list_filename
    lines = []
    # Формат для concat demuxer:
    # file 'C:\path\to\image1.png'
    # duration 2.5
    # file 'C:\path\to\image2.png'
    # duration 3.0
    # ...
    for it in items:
        ipath = it["path"]
        dur = it["duration"]
        # Одинарные кавычки — ffmpeg-friendly; экранировать одиночные кавычки внутри пути (редко нужно в Windows)
        safe_path = ipath.replace("'", r"'\''")
        lines.append(f"file '{safe_path}'")
        lines.append(f"duration {dur}")

    # Повтор последнего файла без duration — чтобы FFmpeg применил последнюю длительность корректно
    last_path = items[-1]["path"].replace("'", r"'\''")
    lines.append(f"file '{last_path}'")

    concat_path.write_text("\n".join(lines), encoding="utf-8")
    return concat_path


# ---------------------------
# Сборка и запуск FFmpeg
# ---------------------------
def build_ffmpeg_cmd(concat_file: Path, video_cfg: dict) -> list[str]:
    w = int(video_cfg["width"])
    h = int(video_cfg["height"])
    bg = str(video_cfg["background"]).lstrip("#")
    if len(bg) not in (6, 8):
        warn(f"Некорректный цвет background '{video_cfg['background']}', используем #000000")
        bg = "000000"

    # Фильтр: вписать и подпаддить
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x{bg}"
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", str(video_cfg["log_level"]),
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", vf,
        "-r", str(video_cfg["fps"]),
    ]

    # Если есть аудио — добавим как второй вход
    if video_cfg.get("audio"):
        audio_path = Path(video_cfg["audio"])
        if not audio_path.is_absolute():
            # Относительный путь — относительно скрипта
            audio_path = (Path(__file__).resolve().parent / audio_path).resolve()
        if not audio_path.exists():
            warn(f"Аудио файл не найден: {audio_path} — игнорируем аудио.")
        else:
            # Сдвиг аудио (если нужен) через -itsoffset
            audio_offset = float(video_cfg.get("audio_offset", 0.0))
            if audio_offset != 0.0:
                cmd += ["-itsoffset", str(audio_offset)]
            cmd += ["-i", str(audio_path)]
            # Маппинг потоков и кодеки
            cmd += [
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:a", "aac",
                "-b:a", "192k",
            ]
            if bool(video_cfg.get("shortest", True)):
                cmd += ["-shortest"]

    # Кодек и качество
    cmd += [
        "-c:v", str(video_cfg["codec"]),
        "-preset", str(video_cfg["preset"]),
        "-crf", str(video_cfg["crf"]),
        "-pix_fmt", str(video_cfg["pixel_format"]),
        "-movflags", "+faststart",
        str(video_cfg["output"]),
    ]

    return cmd


def run_ffmpeg(cmd: list[str]) -> int:
    info("Запуск FFmpeg...")
    info("Команда:\n" + " ".join(shlex.quote(c) for c in cmd))
    try:
        proc = subprocess.run(cmd, check=False)
        return proc.returncode
    except FileNotFoundError:
        err("FFmpeg не найден. Установите FFmpeg и убедитесь, что он доступен в PATH.")
        return 127


# ---------------------------
# main
# ---------------------------
def main() -> None:
    # База — папка скрипта
    base_dir = Path(__file__).resolve().parent
    cfg_path = base_dir / "config.toml"

    info(f"Чтение настроек: {cfg_path}")
    cfg = load_config(cfg_path)

    info("Валидация входных данных…")
    video_cfg, images = validate_and_prepare(cfg, base_dir)

    temp_dir = Path(video_cfg["temp_dir"])
    list_filename = str(video_cfg["list_filename"])

    info("Формирование списка для concat…")
    concat_file = write_concat_list(temp_dir, list_filename, images)

    info("Построение команды FFmpeg…")
    cmd = build_ffmpeg_cmd(concat_file, video_cfg)

    rc = run_ffmpeg(cmd)
    if rc == 0:
        info(f"Готово! Видео: {video_cfg['output']}")
    else:
        err(f"FFmpeg завершился с кодом {rc}")
        sys.exit(rc)


if __name__ == "__main__":
    main()
