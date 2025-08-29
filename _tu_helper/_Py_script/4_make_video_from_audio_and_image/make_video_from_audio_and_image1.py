#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт пакетно делает видео из пар (аудио + картинка).
- Запуск без аргументов.
- Читает config.toml из того же каталога.
- Ищет к каждому аудио одноименные картинки (в т.ч. с суффиксами) — если картинок несколько,
  создаёт видео для КАЖДОЙ, имя видео = имя картинки + ".mp4".
- Если картинки не найдены — аудио пропускается, процесс продолжается.
- Код максимально простой и подробно прокомментирован (на русском).
"""

from __future__ import annotations

import sys
import os
import re
import subprocess
import logging
from pathlib import Path

# В Python 3.11+ есть tomllib в стандартной библиотеке.
# У пользователя Python 3.12, так что просто импортируем tomllib.
try:
    import tomllib  # type: ignore
except Exception as e:
    print("Требуется Python 3.11+ (модуль tomllib). Либо установите 'tomli'. Ошибка:", e)
    sys.exit(1)


# -----------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------

def load_config(config_path: Path) -> dict:
    """Загрузка TOML-конфига."""
    if not config_path.exists():
        print(f"Не найден файл настроек: {config_path}")
        sys.exit(1)
    with config_path.open("rb") as f:
        cfg = tomllib.load(f)
    return cfg


def setup_logging(cfg: dict, script_dir: Path) -> None:
    """Настройка логирования в консоль и файл (по желанию)."""
    log_cfg = cfg.get("logging", {})
    level_name = str(log_cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    log_file = log_cfg.get("file", "")
    if log_file:
        # Если путь относительный — положим рядом со скриптом
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = script_dir / log_path
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )


def normalize_exts(exts: list[str]) -> set[str]:
    """Нормализуем расширения: убираем точки, приводим к нижнему регистру."""
    norm = set()
    for e in exts:
        e = str(e).strip().lower()
        if e.startswith("."):
            e = e[1:]
        if e:
            norm.add(e)
    return norm


def is_audio(path: Path, audio_exts: set[str]) -> bool:
    return path.is_file() and path.suffix.lower().lstrip(".") in audio_exts


def is_image(path: Path, image_exts: set[str]) -> bool:
    return path.is_file() and path.suffix.lower().lstrip(".") in image_exts


def collect_audios_by_mode(cfg: dict, script_dir: Path, audio_exts: set[str]) -> list[Path]:
    """Собираем список аудиофайлов в зависимости от режима."""
    inp = cfg.get("input", {})
    mode = str(inp.get("mode", "dir")).strip().lower()

    collected: list[Path] = []

    if mode == "dir":
        input_dir = inp.get("input_dir", "")
        if not input_dir:
            logging.error("В конфиге input.input_dir не задан.")
            return []

        base = Path(input_dir)
        if not base.is_absolute():
            base = (script_dir / base).resolve()

        recurse = bool(inp.get("recurse", True))
        pattern = "**/*" if recurse else "*"

        for p in base.glob(pattern):
            if is_audio(p, audio_exts):
                collected.append(p)

    elif mode == "file_list":
        file_list_path = inp.get("file_list_path", "")
        if not file_list_path:
            logging.error("В конфиге input.file_list_path не задан.")
            return []

        fl = Path(file_list_path)
        if not fl.is_absolute():
            fl = (script_dir / fl).resolve()
        if not fl.exists():
            logging.error("Файл списка аудио не найден: %s", fl)
            return []

        with fl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p = Path(line)
                if not p.is_absolute():
                    p = (fl.parent / p).resolve()
                if is_audio(p, audio_exts):
                    collected.append(p)
                else:
                    logging.warning("В списке не аудио (или не найдено): %s", p)
    else:
        logging.error("Неизвестный режим input.mode: %s", mode)
        return []

    collected.sort()
    return collected


def build_suffix_checker(stem: str, suffixes_cfg: list[str]) -> callable[[str], bool]:
    """
    Возвращает функцию-предикат: подходит ли имя картинки под допустимые суффиксы.
    - Если suffixes_cfg = ["*"] или пусто — принимаем любой суффикс (включая пустой).
    - Иначе принимаем только указанные ("" — означает точное совпадение без суффикса).
    """
    allow_any = (len(suffixes_cfg) == 0) or (len(suffixes_cfg) == 1 and suffixes_cfg[0] == "*")

    # Предварительно подготовим набор допустимых суффиксов (строгое совпадение)
    allowed = set(suffixes_cfg) if not allow_any else None

    def check(image_stem: str) -> bool:
        if not image_stem.startswith(stem):
            return False
        tail = image_stem[len(stem):]  # суффикс, включая возможное подчеркивание, цифры и т.п.

        if allow_any:
            return True
        else:
            # Разрешаем только те хвосты, что явно перечислены.
            return tail in allowed

    return check


def find_candidate_images(
    audio_path: Path,
    image_exts: set[str],
    image_dirs: list[Path],
    suffixes_cfg: list[str],
) -> list[Path]:
    """
    Ищем все картинки, чьи имена начинаются со стема аудио, и соответствуют политике суффиксов.
    Возвращаем список всех найденных (никакого приоритета — для каждого будет создано видео).
    """
    stem = audio_path.stem
    check_suffix = build_suffix_checker(stem, suffixes_cfg)

    # Папки, где ищем:
    #  - всегда текущая папка аудио
    #  - плюс дополнительные (если заданы)
    search_dirs: list[Path] = [audio_path.parent]
    for d in image_dirs:
        if d not in search_dirs:
            search_dirs.append(d)

    found: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if not is_image(p, image_exts):
                continue
            if check_suffix(p.stem):
                found.append(p)

    # Стабильная сортировка по имени
    found.sort()
    return found


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def choose_output_path(base_dir: Path, name_stem: str, ext: str, on_exists: str) -> Path | None:
    """
    Возвращает путь для сохранения. Если on_exists="skip" и файл уже есть — вернём None.
    Если "rename" — добавим -1, -2... до свободного имени.
    """
    out = base_dir / f"{name_stem}.{ext}"
    if not out.exists():
        return out

    on_exists = on_exists.lower()
    if on_exists == "overwrite":
        return out
    if on_exists == "skip":
        return None
    if on_exists == "rename":
        i = 1
        while True:
            candidate = base_dir / f"{name_stem}-{i}.{ext}"
            if not candidate.exists():
                return candidate
            i += 1
    # на случай некорректного значения — по умолчанию rename
    i = 1
    while True:
        candidate = base_dir / f"{name_stem}-{i}.{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def hex_or_name_color_to_ffmpeg(color: str) -> str:
    """
    FFmpeg в pad принимает цвет вида color=black или color=#RRGGBB.
    Просто возвращаем как есть (удалим лишние пробелы).
    """
    return color.strip()


def build_vfilter(width: int, height: int, scale_mode: str, pad_color: str) -> str:
    """
    Формируем -vf для ffmpeg.
    - fit:  scale=...:force_original_aspect_ratio=decrease, pad=...
    - cover: scale=...:force_original_aspect_ratio=increase, crop=...
    """
    if scale_mode == "cover":
        return (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height}"
        )
    # default -> fit
    color = hex_or_name_color_to_ffmpeg(pad_color)
    return (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={color}"
    )


def run_ffmpeg(
    ffmpeg: Path | str,
    image_path: Path,
    audio_path: Path,
    out_path: Path,
    vf: str,
    fps: int,
    vcodec: str,
    preset: str,
    crf: int,
    pix_fmt: str,
    acodec: str,
    abitrate: str,
    movflags: str | None,
    threads: int | None,
) -> int:
    """
    Запускаем ffmpeg для сборки видео:
      -loop 1                 — зацикленный показ картинки
      -r fps                  — кадры в секунду
      -i image, -i audio      — входы
      -shortest               — длительность по короткому входу (т.е. по аудио)
    """
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel", "error",
        "-y",  # перезапись файла. ВНИМАНИЕ: мы уже выбрали имя согласно on_exists, так что перезапись безопасна
        "-loop", "1",
        "-r", str(fps),
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", vcodec,
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        "-vf", vf,
        "-c:a", acodec,
        "-b:a", abitrate,
        "-shortest",
    ]
    # movflags
    if movflags:
        cmd += ["-movflags", movflags]
    # threads
    if threads and threads > 0:
        cmd += ["-threads", str(threads)]

    cmd += [str(out_path)]

    logging.debug("FFmpeg cmd: %s", " ".join(cmd))
    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except FileNotFoundError:
        logging.error("Не найден ffmpeg. Проверьте ffmpeg_path или PATH.")
        return 1
    except Exception as e:
        logging.exception("Ошибка запуска ffmpeg: %s", e)
        return 1


# -----------------------------
# ОСНОВНОЙ ПРОЦЕСС
# -----------------------------

def main() -> None:
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent

    # 1) Загружаем конфиг
    cfg = load_config(script_dir / "config.toml")

    # 2) Логи
    setup_logging(cfg, script_dir)
    logging.info("Старт make_video_from_audio_and_image")

    # 3) Читаем параметры
    input_cfg = cfg.get("input", {})
    output_cfg = cfg.get("output", {})
    enc = cfg.get("encode", {})

    audio_exts = normalize_exts(input_cfg.get("audio_exts", []))
    image_exts = normalize_exts(input_cfg.get("image_exts", []))

    # Папки для картинок из конфига (если заданы)
    image_search_dirs_cfg = input_cfg.get("image_search_dirs", [])
    image_dirs: list[Path] = []
    for d in image_search_dirs_cfg:
        p = Path(d)
        if not p.is_absolute():
            p = (script_dir / p).resolve()
        image_dirs.append(p)

    # Список допустимых суффиксов
    suffixes_cfg = input_cfg.get("image_suffixes", ["*"])
    suffixes_cfg = [str(s) for s in suffixes_cfg]

    # Выходные параметры
    out_dir = output_cfg.get("dir", "video_output")
    out_dir = Path(out_dir)
    if not out_dir.is_absolute():
        out_dir = (script_dir / out_dir).resolve()
    ensure_dir(out_dir)

    on_exists = str(output_cfg.get("on_exists", "rename")).lower()
    out_ext = str(output_cfg.get("ext", "mp4")).strip().lstrip(".") or "mp4"

    # Кодеки/параметры
    width = int(enc.get("width", 1920))
    height = int(enc.get("height", 1080))
    fps = int(enc.get("fps", 30))
    scale_mode = str(enc.get("scale_mode", "fit")).lower()  # "fit" | "cover"
    pad_color = str(enc.get("pad_color", "#000000"))

    vcodec = str(enc.get("vcodec", "libx264"))
    preset = str(enc.get("preset", "veryfast"))
    crf = int(enc.get("crf", 18))
    pix_fmt = str(enc.get("pix_fmt", "yuv420p"))

    acodec = str(enc.get("acodec", "aac"))
    abitrate = str(enc.get("abitrate", "192k"))
    movflags = enc.get("movflags", "+faststart")
    if not movflags:
        movflags = None

    threads = int(enc.get("threads", 0)) or None

    # Путь к ffmpeg
    ffmpeg_path = str(enc.get("ffmpeg_path", "")).strip()
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else "ffmpeg"

    # 4) Собираем аудио-список
    audios = collect_audios_by_mode(cfg, script_dir, audio_exts)
    if not audios:
        logging.warning("Аудио не найдено. Проверьте input.mode и параметры.")
        return

    logging.info("Найдено аудио-файлов: %d", len(audios))

    # 5) Обработка
    total_video = 0
    for idx, audio in enumerate(audios, 1):
        try:
            logging.info("(%d/%d) Аудио: %s", idx, len(audios), audio)
            # Ищем все подходящие изображения
            images = find_candidate_images(audio, image_exts, image_dirs, suffixes_cfg)
            if not images:
                logging.warning("  Картинка не найдена -> пропуск")
                continue

            # Формируем общий фильтр -vf
            vf = build_vfilter(width, height, scale_mode, pad_color)

            # Для каждого изображения делаем отдельное видео.
            for img in images:
                # Имя видео = имя картинки (stem)
                out_path = choose_output_path(out_dir, img.stem, out_ext, on_exists)
                if out_path is None:
                    logging.info("  Уже существует (skip): %s", img.stem)
                    continue

                logging.info("  Картинка: %s -> Видео: %s", img, out_path.name)
                code = run_ffmpeg(
                    ffmpeg=ffmpeg,
                    image_path=img,
                    audio_path=audio,
                    out_path=out_path,
                    vf=vf,
                    fps=fps,
                    vcodec=vcodec,
                    preset=preset,
                    crf=crf,
                    pix_fmt=pix_fmt,
                    acodec=acodec,
                    abitrate=abitrate,
                    movflags=movflags,
                    threads=threads,
                )
                if code == 0:
                    total_video += 1
                else:
                    logging.error("  Ошибка сборки FFmpeg (код=%s)", code)

        except Exception as e:
            logging.exception("Ошибка при обработке аудио %s: %s", audio, e)
            # Продолжаем со следующим аудио

    logging.info("Готово. Создано видео: %d", total_video)


if __name__ == "__main__":
    main()
