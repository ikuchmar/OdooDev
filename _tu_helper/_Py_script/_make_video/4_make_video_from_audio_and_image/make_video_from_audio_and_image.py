#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Слайдшоу + пакетная сборка видео из аудио и изображений.

Особенности:
- Источники аудио: список папок (mode="dirs") или файл-список (mode="file_list").
- Подбор изображений по тому же стему аудио + разрешённые суффиксы.
- Если найдено несколько картинок:
    * slideshow.enabled = true  -> ОДИН ролик-слайдшоу (тайминги из файла/суффиксов/по умолчанию).
    * slideshow.enabled = false -> отдельный ролик на каждую картинку (имя видео = имя картинки).
- При пустом [output].dir видео кладётся рядом с аудио.
- Анти-«мерцание» статичных картинок: -f image2, fps в фильтре, -vsync cfr, -tune stillimage.
- Управление длительностями слайдов:
    * <audio_stem>.slides.txt (рядом с аудио): числа по порядку, либо "имя/хвост + число", либо "#индекс + число".
    * суффиксы в именах изображений: *_t3.5s.png.
    * Политика подгонки длительностей к длине аудио: stretch_last | scale_all | clip.
- Новое: slideshow.delete_images_after — удалять использованные картинки после успешного рендера.

"""

from __future__ import annotations

import sys
import re
import subprocess
import logging
from pathlib import Path

# Python 3.11+: стандартный tomllib
try:
    import tomllib  # type: ignore
except Exception as e:
    print("Нужен Python 3.11+ (tomllib) или установить tomli. Ошибка:", e)
    sys.exit(1)


# =========================
# Утилиты
# =========================

def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"Не найден файл настроек: {path}")
        sys.exit(1)
    with path.open("rb") as f:
        return tomllib.load(f)

def setup_logging(cfg: dict, script_dir: Path) -> None:
    lc = cfg.get("logging", {})
    lvl = getattr(logging, str(lc.get("level", "INFO")).upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    log_file = str(lc.get("file", "")).strip()
    if log_file:
        p = Path(log_file)
        if not p.is_absolute():
            p = script_dir / p
        handlers.append(logging.FileHandler(p, encoding="utf-8"))
    logging.basicConfig(level=lvl, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)

def normalize_exts(exts: list[str]) -> set[str]:
    out = set()
    for e in exts:
        e = str(e).strip().lower()
        if e.startswith("."):
            e = e[1:]
        if e:
            out.add(e)
    return out

def is_audio(p: Path, audio_exts: set[str]) -> bool:
    return p.is_file() and p.suffix.lower().lstrip(".") in audio_exts

def is_image(p: Path, image_exts: set[str]) -> bool:
    return p.is_file() and p.suffix.lower().lstrip(".") in image_exts

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


# =========================
# Сбор аудио
# =========================

def collect_audios_by_mode(cfg: dict, script_dir: Path, audio_exts: set[str]) -> list[Path]:
    inp = cfg.get("input", {})
    mode = str(inp.get("mode", "dirs")).strip().lower()
    res: list[Path] = []

    if mode == "dirs":
        dirs = inp.get("input_dirs", [])
        if not dirs:
            logging.error("input.input_dirs не задан.")
            return []
        recurse = bool(inp.get("recurse", True))
        pattern = "**/*" if recurse else "*"
        for d in dirs:
            base = Path(str(d))
            if not base.is_absolute():
                base = (script_dir / base).resolve()
            if not base.exists():
                logging.warning("Папка не найдена: %s", base)
                continue
            for p in base.glob(pattern):
                if is_audio(p, audio_exts):
                    res.append(p)

    elif mode == "file_list":
        flp = str(inp.get("file_list_path", "")).strip()
        if not flp:
            logging.error("input.file_list_path не задан.")
            return []
        fl = Path(flp)
        if not fl.is_absolute():
            fl = (script_dir / fl).resolve()
        if not fl.exists():
            logging.error("Файл списка аудио не найден: %s", fl)
            return []
        with fl.open("r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                p = Path(s)
                if not p.is_absolute():
                    p = (fl.parent / p).resolve()
                if is_audio(p, audio_exts):
                    res.append(p)
                else:
                    logging.warning("В списке не аудио/не найдено: %s", p)
    else:
        logging.error("Неизвестный input.mode: %s", mode)
        return []

    res.sort()
    return res


# =========================
# Подбор изображений
# =========================

def build_suffix_checker(stem: str, suffixes: list[str]):
    allow_any = (len(suffixes) == 0) or (len(suffixes) == 1 and suffixes[0] == "*")
    allowed = set(suffixes) if not allow_any else None

    def check(img_stem: str) -> bool:
        if not img_stem.startswith(stem):
            return False
        tail = img_stem[len(stem):]
        if allow_any:
            return True
        return tail in allowed

    return check

def find_candidate_images(audio_path: Path, image_exts: set[str], extra_dirs: list[Path], suffixes: list[str], order: str) -> list[Path]:
    stem = audio_path.stem
    ok = build_suffix_checker(stem, suffixes)

    search_dirs = [audio_path.parent] + [d for d in extra_dirs if d != audio_path.parent]
    items: list[Path] = []
    for d in search_dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if is_image(p, image_exts) and ok(p.stem):
                items.append(p)

    if order == "mtime":
        items.sort(key=lambda p: p.stat().st_mtime)
    else:
        items.sort()
    return items


# =========================
# FFmpeg / фильтры
# =========================

def build_vfilter(width: int, height: int, scale_mode: str, pad_color: str, fps: int) -> str:
    if scale_mode == "cover":
        return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}"
    color = pad_color.strip()
    return f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={color},fps={fps}"

def choose_output_path(base_dir: Path, stem: str, ext: str, on_exists: str) -> Path | None:
    out = base_dir / f"{stem}.{ext}"
    if not out.exists():
        return out
    on_exists = on_exists.lower()
    if on_exists == "overwrite":
        return out
    if on_exists == "skip":
        return None
    i = 1
    while True:
        c = base_dir / f"{stem}-{i}.{ext}"
        if not c.exists():
            return c
        i += 1

def run_ffmpeg_still(ffmpeg: Path | str, image: Path, audio: Path, out_path: Path, vf: str,
                     vcodec: str, preset: str, crf: int, pix_fmt: str,
                     acodec: str, abitrate: str, movflags: str | None, threads: int | None) -> int:
    cmd = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "image2", "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-c:v", vcodec, "-preset", preset, "-crf", str(crf), "-pix_fmt", pix_fmt, "-tune", "stillimage",
        "-vf", vf, "-vsync", "cfr",
        "-c:a", acodec, "-b:a", abitrate,
        "-shortest",
    ]
    if movflags:
        cmd += ["-movflags", movflags]
    if threads and threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [str(out_path)]
    logging.debug("FFmpeg (still): %s", " ".join(cmd))
    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        logging.error("Не найден ffmpeg. Проверьте encode.ffmpeg_path или PATH.")
        return 1
    except Exception as e:
        logging.exception("Ошибка FFmpeg (still): %s", e)
        return 1

def ffprobe_duration_seconds(ffmpeg_path_or_name: str | Path, audio_path: Path) -> float | None:
    candidates = []
    if isinstance(ffmpeg_path_or_name, Path) and ffmpeg_path_or_name.name.lower().startswith("ffmpeg"):
        probe = ffmpeg_path_or_name.parent / "ffprobe.exe"
        if probe.exists():
            candidates.append(str(probe))
    candidates.append("ffprobe")
    for exe in candidates:
        try:
            out = subprocess.check_output(
                [exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(audio_path)],
                stderr=subprocess.PIPE
            )
            val = float(out.decode("utf-8", "ignore").strip())
            if val > 0:
                return val
        except Exception:
            continue
    return None

def run_ffmpeg_slideshow_equal(ffmpeg: Path | str, images: list[Path], per_sec: list[float], audio: Path, out_path: Path,
                               vf_one: str, vcodec: str, preset: str, crf: int, pix_fmt: str,
                               acodec: str, abitrate: str, movflags: str | None, threads: int | None) -> int:
    """
    Слайдшоу без переходов, индивидуальные длительности per_sec[i].
    Каждую картинку подаём как -f image2 -loop 1 -t <sec>.
    filter_complex: [i:v] vf -> [vi]; concat=n=N:v=1:a=0 [vc]
    map [vc] + аудио.
    """
    assert len(images) == len(per_sec)
    cmd = [str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y"]

    for img, sec in zip(images, per_sec):
        sec = max(0.001, float(sec))
        cmd += ["-f", "image2", "-loop", "1", "-t", f"{sec:.6f}", "-i", str(img)]
    cmd += ["-i", str(audio)]

    fc = []
    for i in range(len(images)):
        fc.append(f"[{i}:v]{vf_one}[v{i}]")
    fc.append("".join(f"[v{i}]" for i in range(len(images))) + f"concat=n={len(images)}:v=1:a=0[vc]")
    filter_complex = ";".join(fc)

    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[vc]",
        "-map", f"{len(images)}:a:0",
        "-c:v", vcodec, "-preset", preset, "-crf", str(crf), "-pix_fmt", pix_fmt, "-vsync", "cfr", "-tune", "stillimage",
        "-c:a", acodec, "-b:a", abitrate,
        "-shortest",
    ]
    if movflags:
        cmd += ["-movflags", movflags]
    if threads and threads > 0:
        cmd += ["-threads", str(threads)]
    cmd += [str(out_path)]

    logging.debug("FFmpeg (slideshow): %s", " ".join(cmd))
    try:
        return subprocess.run(cmd, check=False).returncode
    except FileNotFoundError:
        logging.error("Не найден ffmpeg. Проверьте encode.ffmpeg_path или PATH.")
        return 1
    except Exception as e:
        logging.exception("Ошибка FFmpeg (slideshow): %s", e)
        return 1


# =========================
# Парсинг таймингов
# =========================

DUR_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*$")
NAME_DUR_RE = re.compile(r"^\s*(.+?)\s+(\d+(?:\.\d+)?)\s*$")
INDEX_DUR_RE = re.compile(r"^\s*#(\d+)\s+(\d+(?:\.\d+)?)\s*$")
SUFFIX_DUR_IN_NAME_RE = re.compile(r"_t(\d+(?:\.\d+)?)s$", re.IGNORECASE)

def parse_timings_file(timings_path: Path, images: list[Path]) -> list[float] | None:
    """
    Читает <audio_stem>.slides.txt и возвращает список длительностей (float|None) длиной len(images),
    в порядке найденных картинок; None если файла нет/пустой.
    Поддерживаемые строки:
      "3.0"
      "bg.png 2.5" или "_bg 2.5"   (сопоставление по окончанию имени)
      "#3 1.2"
    """
    if not timings_path.exists():
        return None
    with timings_path.open("r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return None

    per: list[float | None] = [None] * len(images)
    seq_idx = 0

    def set_by_name_tail(tail: str, val: float) -> bool:
        for i, p in enumerate(images):
            if p.name.endswith(tail):
                per[i] = val
                return True
        return False

    for s in lines:
        m = INDEX_DUR_RE.match(s)
        if m:
            idx = int(m.group(1)) - 1
            dur = float(m.group(2))
            if 0 <= idx < len(images):
                per[idx] = dur
            continue
        m = NAME_DUR_RE.match(s)
        if m:
            tail = m.group(1).strip()
            dur = float(m.group(2))
            if not set_by_name_tail(tail, dur):
                logging.warning("timings: не найден слайд по '%s'", tail)
            continue
        m = DUR_RE.match(s)
        if m:
            dur = float(m.group(1))
            if seq_idx < len(images):
                per[seq_idx] = dur
                seq_idx += 1
            continue
        logging.warning("timings: строка не распознана: %s", s)

    return per

def durations_from_suffixes(images: list[Path]) -> list[float | None]:
    out: list[float | None] = []
    for p in images:
        m = SUFFIX_DUR_IN_NAME_RE.search(p.stem)
        out.append(float(m.group(1)) if m else None)
    return out

def fill_and_fit_durations(per_in: list[float | None], audio_dur: float, min_image_sec: float, policy: str) -> list[float]:
    """
    Дополняет отсутствующие длительности равными долями оставшегося времени,
    затем подгоняет под длину аудио согласно policy.
    """
    n = len(per_in)
    per = per_in[:]
    # 1) заполнить None
    unspecified = [i for i, v in enumerate(per) if v is None]
    specified_sum = sum(v for v in per if isinstance(v, float))
    remain = max(0.0, audio_dur - specified_sum)
    if unspecified:
        share = max(min_image_sec, remain / len(unspecified)) if remain > 0 else min_image_sec
        for i in unspecified:
            per[i] = share  # type: ignore

    per_f = [float(v) for v in per]  # type: ignore

    # 2) подгонка
    total = sum(per_f)
    if total <= 0:
        per_f = [max(min_image_sec, audio_dur / max(1, n))] * n
        total = sum(per_f)

    diff = audio_dur - total
    policy = policy.lower()
    if abs(diff) < 1e-6:
        return per_f

    if policy == "stretch_last":
        per_f[-1] = max(min_image_sec, per_f[-1] + diff)
    elif policy == "scale_all":
        k = audio_dur / total if total > 0 else 1.0
        per_f = [max(min_image_sec, v * k) for v in per_f]
    elif policy == "clip":
        pass  # не корректируем
    else:
        per_f[-1] = max(min_image_sec, per_f[-1] + diff)
    return per_f


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
    slide = cfg.get("slideshow", {})

    audio_exts = normalize_exts(input_cfg.get("audio_exts", []))
    image_exts = normalize_exts(input_cfg.get("image_exts", []))

    image_dirs: list[Path] = []
    for d in input_cfg.get("image_search_dirs", []):
        p = Path(str(d))
        if not p.is_absolute():
            p = (script_dir / p).resolve()
        image_dirs.append(p)

    suffixes = [str(s) for s in input_cfg.get("image_suffixes", ["*"])]

    # Слайдшоу/тайминги/удаление
    slideshow_enabled = bool(slide.get("enabled", True))
    order = str(slide.get("order", "name")).lower()
    source = str(slide.get("source", "auto")).lower()              # auto|file|suffix|auto_equal
    timings_ext = str(slide.get("timings_file_ext", ".slides.txt"))
    min_image_sec = float(slide.get("min_image_sec", 0.3))
    fill_policy = str(slide.get("fill_policy", "stretch_last")).lower()
    delete_images_after = bool(slide.get("delete_images_after", False))

    # Выход
    out_dir_cfg = str(output_cfg.get("dir", "")).strip()
    on_exists = str(output_cfg.get("on_exists", "rename")).lower()
    out_ext = str(output_cfg.get("ext", "mp4")).strip().lstrip(".") or "mp4"

    # Кодеки/параметры
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

    # Аудио
    audios = collect_audios_by_mode(cfg, script_dir, audio_exts)
    if not audios:
        logging.warning("Аудио не найдено.")
        return
    logging.info("Найдено аудио-файлов: %d", len(audios))

    vf_common = build_vfilter(width, height, scale_mode, pad_color, fps)

    total_video = 0
    for idx, audio in enumerate(audios, 1):
        try:
            logging.info("(%d/%d) Аудио: %s", idx, len(audios), audio)
            images = find_candidate_images(audio, image_exts, image_dirs, suffixes, order)
            if not images:
                logging.warning("  Картинка не найдена -> пропуск")
                continue

            # Папка вывода
            if out_dir_cfg:
                base_out = Path(out_dir_cfg)
                if not base_out.is_absolute():
                    base_out = (script_dir / base_out).resolve()
                ensure_dir(base_out)
            else:
                base_out = audio.parent

            if not slideshow_enabled or len(images) == 1:
                # --------- Обычный режим: ролик на каждую картинку ---------
                for img in images:
                    out_path = choose_output_path(base_out, img.stem, out_ext, on_exists)
                    if out_path is None:
                        logging.info("  Уже существует (skip): %s", (base_out / f"{img.stem}.{out_ext}").name)
                        continue

                    logging.info("  Картинка: %s -> Видео: %s", img, out_path.name)
                    code = run_ffmpeg_still(ffmpeg, img, audio, out_path, vf_common,
                                            vcodec, preset, crf, pix_fmt, acodec, abitrate, movflags, threads)
                    if code == 0:
                        total_video += 1
                        if delete_images_after:
                            try:
                                img.unlink()
                                logging.info("  Удалена картинка: %s", img)
                            except Exception as e:
                                logging.warning("  Не удалось удалить %s: %s", img, e)
                    else:
                        logging.error("  Ошибка FFmpeg (still), код=%s", code)
                continue

            # --------- СЛАЙДШОУ: один ролик ---------
            out_path = choose_output_path(base_out, audio.stem, out_ext, on_exists)
            if out_path is None:
                logging.info("  Уже существует (skip): %s", (base_out / f"{audio.stem}.{out_ext}").name)
                continue

            audio_dur = ffprobe_duration_seconds(ffmpeg if isinstance(ffmpeg, Path) else Path("ffmpeg"), audio)
            if not audio_dur or audio_dur <= 0:
                logging.warning("  Не удалось получить длительность аудио; примем 1.0 с/кадр.")
                audio_dur = 1.0 * len(images)

            # Источник таймингов
            per_list: list[float | None] | None = None
            if source in ("file", "auto", "auto_equal"):
                timings_file = audio.with_name(f"{audio.stem}{timings_ext}")
                per_list = parse_timings_file(timings_file, images)
            if (per_list is None) and (source in ("suffix", "auto")):
                per_list = durations_from_suffixes(images)
            if per_list is None:
                per_list = [None] * len(images)

            per_final = fill_and_fit_durations(per_list, audio_dur, min_image_sec, fill_policy)

            logging.info("  Слайдшоу: кадров=%d, policy=%s, sum=%.3fs, итог: %s",
                         len(images), fill_policy, sum(per_final), out_path.name)

            code = run_ffmpeg_slideshow_equal(
                ffmpeg=ffmpeg, images=images, per_sec=per_final, audio=audio,
                out_path=out_path, vf_one=vf_common,
                vcodec=vcodec, preset=preset, crf=crf, pix_fmt=pix_fmt,
                acodec=acodec, abitrate=abitrate, movflags=movflags, threads=threads
            )
            if code == 0:
                total_video += 1
                if delete_images_after:
                    for img in images:
                        try:
                            img.unlink()
                            logging.info("  Удалена картинка: %s", img)
                        except Exception as e:
                            logging.warning("  Не удалось удалить %s: %s", img, e)
            else:
                logging.error("  Ошибка FFmpeg (slideshow), код=%s", code)

        except Exception as e:
            logging.exception("Ошибка при обработке %s: %s", audio, e)

    logging.info("Готово. Создано видео: %d", total_video)


if __name__ == "__main__":
    main()
