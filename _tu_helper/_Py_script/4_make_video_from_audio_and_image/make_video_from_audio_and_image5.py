#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Пакетно создаёт видео из аудио + изображений.

Фишки:
- Источники аудио: список папок (mode="dirs") или файл-список (mode="file_list").
- Подбор изображений по тому же стему + разрешённые суффиксы.
- Если найдено несколько картинок:
    * slideshow.enabled = true  -> ОДИН ролик-слайдшоу: картинки делят длительность аудио поровну.
    * slideshow.enabled = false -> как раньше: отдельный ролик на каждую картинку (имя видео = имя картинки).
- Если [output].dir пусто -> сохраняем видео рядом с аудио.
- Анти-«мерцание» статичных картинок: читаем как статичное изображение (-f image2), fps задаём через фильтр, -vsync cfr, -tune stillimage.

Примечание: для слайдшоу равные интервалы считаются через ffprobe-длительность аудио.
"""

from __future__ import annotations

import sys
import subprocess
import logging
from pathlib import Path

# Python 3.11+: стандартный tomllib
try:
    import tomllib  # type: ignore
except Exception as e:
    print("Требуется Python 3.11+ (модуль tomllib). Либо установите 'tomli'. Ошибка:", e)
    sys.exit(1)


# =========================
# Утилиты
# =========================

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        print(f"Не найден файл настроек: {config_path}")
        sys.exit(1)
    with config_path.open("rb") as f:
        return tomllib.load(f)


def setup_logging(cfg: dict, script_dir: Path) -> None:
    log_cfg = cfg.get("logging", {})
    level_name = str(log_cfg.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = str(log_cfg.get("file", "")).strip()
    if log_file:
        log_path = Path(log_file)
        if not log_path.is_absolute():
            log_path = script_dir / log_path
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)


def normalize_exts(exts: list[str]) -> set[str]:
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
    """
    Собираем список аудиофайлов:
    - mode="dirs": из всех папок input_dirs (recurse=True/False)
    - mode="file_list": из файла со списком путей
    """
    inp = cfg.get("input", {})
    mode = str(inp.get("mode", "dirs")).strip().lower()
    collected: list[Path] = []

    if mode == "dirs":
        input_dirs = inp.get("input_dirs", [])
        if not input_dirs:
            logging.error("В конфиге input.input_dirs не задан.")
            return []
        recurse = bool(inp.get("recurse", True))
        pattern = "**/*" if recurse else "*"

        for dir_path in input_dirs:
            base = Path(str(dir_path))
            if not base.is_absolute():
                base = (script_dir / base).resolve()
            if not base.exists():
                logging.warning("Папка не найдена: %s", base)
                continue
            for p in base.glob(pattern):
                if is_audio(p, audio_exts):
                    collected.append(p)

    elif mode == "file_list":
        file_list_path = str(inp.get("file_list_path", "")).strip()
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


def build_suffix_checker(stem: str, suffixes_cfg: list[str]):
    """
    Предикат: подходит ли image_stem под допустимые суффиксы.
    - ["*"] или пусто => любой суффикс (включая пустой).
    - Иначе принимаем только строго перечисленные ("" — точное совпадение без суффикса).
    """
    allow_any = (len(suffixes_cfg) == 0) or (len(suffixes_cfg) == 1 and suffixes_cfg[0] == "*")
    allowed = set(suffixes_cfg) if not allow_any else None

    def check(image_stem: str) -> bool:
        if not image_stem.startswith(stem):
            return False
        tail = image_stem[len(stem):]
        if allow_any:
            return True
        return tail in allowed

    return check


def find_candidate_images(audio_path: Path, image_exts: set[str], image_dirs: list[Path], suffixes_cfg: list[str], order: str) -> list[Path]:
    """
    Ищем все картинки, чьи имена начинаются со стема аудио и проходят политику суффиксов.
    Сортировка: order="name" | "mtime"
    """
    stem = audio_path.stem
    check_suffix = build_suffix_checker(stem, suffixes_cfg)

    search_dirs: list[Path] = [audio_path.parent]
    for d in image_dirs:
        if d not in search_dirs:
            search_dirs.append(d)

    found: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if is_image(p, image_exts) and check_suffix(p.stem):
                found.append(p)

    if order == "mtime":
        found.sort(key=lambda p: p.stat().st_mtime)
    else:
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
    # rename по умолчанию
    i = 1
    while True:
        candidate = base_dir / f"{name_stem}-{i}.{ext}"
        if not candidate.exists():
            return candidate
        i += 1


def hex_or_name_color_to_ffmpeg(color: str) -> str:
    return color.strip()


def build_vfilter(width: int, height: int, scale_mode: str, pad_color: str, fps: int) -> str:
    """
    Формируем -vf:
    - fit:   scale=...:decrease, pad=..., fps=N
    - cover: scale=...:increase, crop=..., fps=N
    """
    if scale_mode == "cover":
        return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}"
    color = hex_or_name_color_to_ffmpeg(pad_color)
    return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={color},fps={fps}"


def run_ffmpeg_still(
    ffmpeg: Path | str,
    image_path: Path,
    audio_path: Path,
    out_path: Path,
    vf: str,
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
    Обычный режим (не слайдшоу): один ролик из одной картинки.
    Анти-«мерцание»: -f image2, fps в фильтре, -vsync cfr, -tune stillimage
    """
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-loglevel", "error",
        "-y",

        "-f", "image2",
        "-loop", "1",
        "-i", str(image_path),

        "-i", str(audio_path),

        "-c:v", vcodec,
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        "-tune", "stillimage",

        "-vf", vf,
        "-vsync", "cfr",

        "-c:a", acodec,
        "-b:a", abitrate,

        "-shortest",
    ]
    if movflags:
        cmd += ["-movflags", movflags]
    if threads and threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [str(out_path)]

    logging.debug("FFmpeg cmd: %s", " ".join(cmd))
    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except FileNotFoundError:
        logging.error("Не найден ffmpeg. Проверьте encode.ffmpeg_path или PATH.")
        return 1
    except Exception as e:
        logging.exception("Ошибка запуска ffmpeg: %s", e)
        return 1


def ffprobe_duration_seconds(ffprobe_or_ffmpeg: str | Path, audio_path: Path) -> float | None:
    """
    Возвращает длительность аудио в секундах (float) через ffprobe.
    Обычно в составе ffmpeg есть ffprobe (рядом в PATH).
    Если ffprobe не найден, попробуем 'ffprobe' по PATH.
    """
    candidates = []
    if isinstance(ffprobe_or_ffmpeg, Path):
        # если передали путь к ffmpeg.exe — попробуем рядом ffprobe.exe
        p = ffprobe_or_ffmpeg
        if p.name.lower().startswith("ffmpeg"):
            probe = p.parent / "ffprobe.exe"
            if probe.exists():
                candidates.append(str(probe))
    candidates += ["ffprobe"]  # по PATH

    for exe in candidates:
        try:
            # Вывод только числа
            cmd = [
                exe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nk=1:nw=1",
                str(audio_path),
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.PIPE)
            s = out.decode("utf-8", errors="ignore").strip()
            val = float(s)
            if val > 0:
                return val
        except Exception:
            continue
    return None


def run_ffmpeg_slideshow_equal(
    ffmpeg: Path | str,
    images: list[Path],
    per_image_sec: float,
    audio_path: Path,
    out_path: Path,
    vf_for_one: str,   # фильтр, который применим к каждому кадру (scale/pad + fps)
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
    Слайдшоу без переходов: каждый кадр показывается per_image_sec, затем конкатенация.
    Техника:
      - Для КАЖДОЙ картинки: отдельный вход (-f image2 -loop 1 -t per)
      - В filter_complex:
         [0:v] vf -> [v0]; [1:v] vf -> [v1]; ...; затем concat=n=N:v=1:a=0 [vc]
      - map видео [vc] + аудио (последний вход)
      - -shortest (страховка)
    """
    # Входы: N картинок + 1 аудио
    cmd = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y"]

    for img in images:
        cmd += ["-f", "image2", "-loop", "1", "-t", f"{per_image_sec:.6f}", "-i", str(img)]
    cmd += ["-i", str(audio_path)]

    # Строим filter_complex
    fc_parts = []
    for i in range(len(images)):
        fc_parts.append(f"[{i}:v]{vf_for_one}[v{i}]")
    # concat
    vnames = "".join([f"[v{i}]" for i in range(len(images))])
    fc_parts.append(f"{vnames}concat=n={len(images)}:v=1:a=0[vc]")

    filter_complex = ";".join(fc_parts)

    # Основные кодеки/параметры
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vc]",
        "-map", f"{len(images)}:a:0",  # аудио — последний вход
        "-c:v", vcodec,
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", pix_fmt,
        "-vsync", "cfr",
        "-tune", "stillimage",
        "-c:a", acodec,
        "-b:a", abitrate,
        "-shortest",
    ]
    if movflags:
        cmd += ["-movflags", movflags]
    if threads and threads > 0:
        cmd += ["-threads", str(threads)]

    cmd += [str(out_path)]

    logging.debug("FFmpeg (slideshow) cmd: %s", " ".join(cmd))

    try:
        res = subprocess.run(cmd, check=False)
        return res.returncode
    except FileNotFoundError:
        logging.error("Не найден ffmpeg. Проверьте encode.ffmpeg_path или PATH.")
        return 1
    except Exception as e:
        logging.exception("Ошибка запуска ffmpeg (slideshow): %s", e)
        return 1


# =========================
# Основной процесс
# =========================

def main() -> None:
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent

    cfg = load_config(script_dir / "config.toml")
    setup_logging(cfg, script_dir)
    logging.info("Старт make_video_from_audio_and_image")

    input_cfg = cfg.get("input", {})
    output_cfg = cfg.get("output", {})
    enc = cfg.get("encode", {})
    slide_cfg = cfg.get("slideshow", {})

    audio_exts = normalize_exts(input_cfg.get("audio_exts", []))
    image_exts = normalize_exts(input_cfg.get("image_exts", []))

    # Доп. каталоги для картинок (если заданы)
    image_dirs: list[Path] = []
    for d in input_cfg.get("image_search_dirs", []):
        p = Path(str(d))
        if not p.is_absolute():
            p = (script_dir / p).resolve()
        image_dirs.append(p)

    # Разрешённые суффиксы
    suffixes_cfg = [str(s) for s in input_cfg.get("image_suffixes", ["*"])]

    # Слайдшоу
    slideshow_enabled = bool(slide_cfg.get("enabled", True))
    order = str(slide_cfg.get("order", "name")).lower()
    min_image_sec = float(slide_cfg.get("min_image_sec", 0.3))
    if min_image_sec <= 0:
        min_image_sec = 0.3

    # Выходные параметры
    out_dir_cfg = str(output_cfg.get("dir", "")).strip()  # "" => рядом с аудио
    on_exists = str(output_cfg.get("on_exists", "rename")).lower()
    out_ext = str(output_cfg.get("ext", "mp4")).strip().lstrip(".") or "mp4"

    # Параметры кодирования
    width = int(enc.get("width", 1920))
    height = int(enc.get("height", 1080))
    fps = int(enc.get("fps", 30))
    scale_mode = str(enc.get("scale_mode", "fit")).lower()
    pad_color = str(enc.get("pad_color", "#000000"))
    vcodec = str(enc.get("vcodec", "libx264"))
    preset = str(enc.get("preset", "veryfast"))
    crf = int(enc.get("crf", 18))
    pix_fmt = str(enc.get("pix_fmt", "yuv420p"))
    acodec = str(enc.get("acodec", "aac"))
    abitrate = str(enc.get("abitrate", "192k"))
    movflags = enc.get("movflags", "+faststart") or None
    threads = int(enc.get("threads", 0)) or None

    # ffmpeg
    ffmpeg_path = str(enc.get("ffmpeg_path", "")).strip()
    ffmpeg = Path(ffmpeg_path) if ffmpeg_path else "ffmpeg"

    # Список аудио
    audios = collect_audios_by_mode(cfg, script_dir, audio_exts)
    if not audios:
        logging.warning("Аудио не найдено. Проверьте input.mode и параметры.")
        return
    logging.info("Найдено аудио-файлов: %d", len(audios))

    vf_common = build_vfilter(width, height, scale_mode, pad_color, fps)

    total_video = 0
    for idx, audio in enumerate(audios, 1):
        try:
            logging.info("(%d/%d) Аудио: %s", idx, len(audios), audio)
            images = find_candidate_images(audio, image_exts, image_dirs, suffixes_cfg, order)
            if not images:
                logging.warning("  Картинка не найдена -> пропуск")
                continue

            # Базовая папка вывода
            if out_dir_cfg:
                base_out_dir = Path(out_dir_cfg)
                if not base_out_dir.is_absolute():
                    base_out_dir = (script_dir / base_out_dir).resolve()
                ensure_dir(base_out_dir)
            else:
                base_out_dir = audio.parent  # рядом с аудио

            if slideshow_enabled and len(images) > 1:
                # --------- СЛАЙДШОУ: один ролик ---------
                # Имя по стему АУДИО:
                out_path = choose_output_path(base_out_dir, audio.stem, out_ext, on_exists)
                if out_path is None:
                    logging.info("  Уже существует (skip): %s", (base_out_dir / f"{audio.stem}.{out_ext}").name)
                    continue

                # Длительность аудио
                dur = ffprobe_duration_seconds(ffmpeg if isinstance(ffmpeg, Path) else Path("ffmpeg"), audio)
                if not dur or dur <= 0:
                    logging.warning("  Не удалось получить длительность аудио через ffprobe; "
                                    "будет использовано 1.0 сек/картинку как запасной вариант.")
                    per = 1.0
                else:
                    per = max(min_image_sec, dur / len(images))

                logging.info("  Слайдшоу: кадров=%d, per_image=%.3fs, итоговый файл: %s",
                             len(images), per, out_path.name)

                code = run_ffmpeg_slideshow_equal(
                    ffmpeg=ffmpeg,
                    images=images,
                    per_image_sec=per,
                    audio_path=audio,
                    out_path=out_path,
                    vf_for_one=vf_common,
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
                    logging.error("  Ошибка FFmpeg (slideshow), код=%s", code)

            else:
                # --------- Обычный режим: ролик на каждую картинку ---------
                for img in images:
                    out_path = choose_output_path(base_out_dir, img.stem, out_ext, on_exists)
                    if out_path is None:
                        logging.info("  Уже существует (skip): %s", (base_out_dir / f"{img.stem}.{out_ext}").name)
                        continue

                    logging.info("  Картинка: %s -> Видео: %s", img, out_path.name)
                    code = run_ffmpeg_still(
                        ffmpeg=ffmpeg,
                        image_path=img,
                        audio_path=audio,
                        out_path=out_path,
                        vf=vf_common,
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
                        logging.error("  Ошибка FFmpeg (still), код=%s", code)

        except Exception as e:
            logging.exception("Ошибка при обработке аудио %s: %s", audio, e)

    logging.info("Готово. Создано видео: %d", total_video)


if __name__ == "__main__":
    main()
