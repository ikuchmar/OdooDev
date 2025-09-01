#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация изображений через OpenAI для каждого ТЕКСТОВОГО файла в input_dirs/input_files.
- Ищет *.txt, *.md (настраивается text_exts)
- include/exclude по суффиксам (как в твоих скриптах)
- Вывод в output_dir (или рядом), c зеркалированием подпапок
- «Размеры как во вложении»: после генерации можно доресайзить в width/height
Требуется: Python 3.11+ (tomllib), openai>=1.0.0, Pillow
pip install openai Pillow
"""

from __future__ import annotations
import os
import io
import base64
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- TOML ---
try:
    import tomllib  # Python 3.11+
except Exception:
    print("❌ Нужен Python 3.11+ (есть модуль tomllib).")
    raise

# --- OpenAI ---
try:
    from openai import OpenAI
except Exception:
    print("❌ Не установлен пакет openai. Установите: pip install openai")
    raise

# --- Pillow ---
try:
    from PIL import Image
except Exception:
    print("❌ Не установлен Pillow (PIL). Установите: pip install Pillow")
    raise


# =========================
# Утилиты
# =========================

def script_dir() -> Path:
    return Path(__file__).resolve().parent

def load_config() -> Dict[str, Any]:
    cfg_path = script_dir() / "config.toml"
    if not cfg_path.exists():
        print(f"❌ Не найден файл настроек: {cfg_path}")
        raise SystemExit(1)
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)

def log_print(msg: str, log_fp: Optional[io.TextIOBase]):
    print(msg)
    if log_fp:
        log_fp.write(msg + "\n")
        log_fp.flush()

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def safe_name_with_suffix(target: Path) -> Path:
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    parent = target.parent
    i = 1
    while True:
        cand = parent / f"{stem}_{i}{suffix}"
        if not cand.exists():
            return cand
        i += 1

def passes_suffix_filters(stem: str, cfg: Dict[str, Any]) -> bool:
    excl = [s.lower() for s in (cfg.get("exclude_suffixes") or [])]
    incl = [s.lower() for s in (cfg.get("include_suffixes") or [])]
    s = stem.lower()
    for suf in excl:
        if suf and s.endswith(suf):
            return False
    if incl:
        return any(s.endswith(suf) for suf in incl if suf)
    return True

def get_all_input_dirs(cfg: Dict[str, Any]) -> List[Path]:
    dirs: List[Path] = []
    if "input_dir" in cfg and cfg["input_dir"]:
        d = str(cfg["input_dir"]).strip()
        if d:
            dirs.append(Path(d))
    if "input_dirs" in cfg and cfg["input_dirs"]:
        for d in cfg["input_dirs"]:
            s = str(d).strip()
            if s:
                dirs.append(Path(s))
    # уникализация
    res, seen = [], set()
    for p in dirs:
        rp = p.resolve()
        if rp not in seen:
            res.append(rp)
            seen.add(rp)
    return res

def is_text_file(path: Path, text_exts: List[str]) -> bool:
    return path.suffix.lower() in [e.lower() for e in text_exts]

def collect_text_files(cfg: Dict[str, Any], log_fp: Optional[io.TextIOBase]) -> List[Path]:
    text_exts = cfg.get("text_exts") or [".txt", ".md"]
    recursive = bool(cfg.get("recursive", True))
    input_files = cfg.get("input_files") or []

    files: List[Path] = []

    # из папок
    for base in get_all_input_dirs(cfg):
        if base.exists() and base.is_dir():
            pattern = "**/*" if recursive else "*"
            for p in base.glob(pattern):
                if p.is_file() and is_text_file(p, text_exts):
                    if passes_suffix_filters(p.stem, cfg):
                        files.append(p.resolve())
                    else:
                        log_print(f"🚫 Фильтр суффиксов исключил: {p.name}", log_fp)
        else:
            log_print(f"⚠️  input_dir не существует или не папка: {base}", log_fp)

    # явные файлы
    for f in input_files:
        p = Path(f)
        if p.exists() and p.is_file():
            if is_text_file(p, text_exts):
                if passes_suffix_filters(p.stem, cfg):
                    files.append(p.resolve())
                else:
                    log_print(f"🚫 Фильтр суффиксов исключил: {p.name}", log_fp)
            else:
                log_print(f"⚠️  В input_files встречен не-текстовый файл: {p}", log_fp)
        else:
            log_print(f"⚠️  В input_files путь не найден: {p}", log_fp)

    uniq = sorted(set(files))
    log_print(f"Найдено текстовых файлов (после фильтрации): {len(uniq)}", log_fp)
    return uniq

def compute_output_path(in_file: Path, cfg: Dict[str, Any], image_format: str) -> Path:
    out_dir_cfg = (cfg.get("output_dir") or "").strip()
    mirror = bool(cfg.get("mirror_subdirs", True))
    suffix = (cfg.get("output_suffix") or "").strip()

    if not out_dir_cfg:
        target_dir = in_file.parent
    else:
        base_out = Path(out_dir_cfg)
        if not mirror:
            target_dir = base_out
        else:
            rel_dir: Optional[Path] = None
            for base_in in get_all_input_dirs(cfg):
                try:
                    rel_dir = in_file.parent.resolve().relative_to(base_in.resolve())
                    break
                except Exception:
                    continue
            target_dir = base_out / rel_dir if rel_dir is not None else base_out

    ensure_dir(target_dir)
    stem = in_file.stem + suffix if suffix else in_file.stem
    return target_dir / f"{stem}.{image_format.lower()}"

def save_image_bytes(img_bytes: bytes, path: Path, cfg_img: Dict[str, Any], conflicts: str,
                     dry_run: bool, log_fp: Optional[io.TextIOBase]):
    image_format = (cfg_img.get("format") or "png").lower()
    conflicts = (conflicts or "skip").lower()

    target = path
    if target.exists():
        if conflicts == "skip":
            log_print(f"⏭️  Уже существует, пропускаем: {target}", log_fp)
            return
        if conflicts == "rename":
            target = safe_name_with_suffix(target)
        elif conflicts == "overwrite":
            pass
        else:
            log_print(f"⚠️  Неизвестная политика conflicts='{conflicts}', считаем как 'skip'", log_fp)
            return

    if dry_run:
        log_print(f"[dry-run] Сохранили бы: {target}", log_fp)
        return

    # Сохраняем как PNG временно (base64 у OpenAI — PNG/WEBP), потом при необходимости ресайзим/конвертим
    tmp = target.with_suffix(".tmp.png")
    with open(tmp, "wb") as f:
        f.write(img_bytes)

    # Ресайз/конверсия «как во вложении»
    resize_after = bool(cfg_img.get("resize_after", False))
    width = int(cfg_img.get("width", 1920))
    height = int(cfg_img.get("height", 1080))
    jpeg_quality = int(cfg_img.get("jpeg_quality", 90))

    img = Image.open(tmp).convert("RGBA")

    if resize_after:
        img = img.resize((width, height), Image.LANCZOS)

    # Конвертация формата
    if image_format in ("jpg", "jpeg", "webp"):
        out = Image.new("RGB", img.size, (255, 255, 255))
        out.paste(img, mask=img.split()[-1] if "A" in img.getbands() else None)
        save_kwargs = {"quality": max(1, min(95, jpeg_quality))}
        out.save(target, format=image_format.upper(), **save_kwargs)
    else:
        img.save(target, format="PNG")

    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass

    log_print(f"💾 Сохранено: {target}", log_fp)


# =========================
# Работа с промптом
# =========================

def build_prompt_for_file(path: Path, cfg_openai: Dict[str, Any]) -> str:
    mode = (cfg_openai.get("prompt_from") or "first_line").lower()
    prefix = cfg_openai.get("prompt_prefix") or ""
    suffix = cfg_openai.get("prompt_suffix") or ""
    max_chars = int(cfg_openai.get("max_chars", 1200))

    text = ""
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        raw = path.read_text(encoding="cp1251", errors="ignore")

    if mode == "filename":
        core = path.stem
    elif mode == "content":
        core = " ".join(raw.split())  # схлопнуть пробелы/переводы строк
        if len(core) > max_chars:
            core = core[:max_chars] + "..."
    else:  # "first_line"
        core = ""
        for line in raw.splitlines():
            s = line.strip()
            if s:
                core = s
                break
        if not core:
            core = path.stem

    text = f"{prefix}{core}{suffix}"
    return text.strip()


# =========================
# Основной процесс
# =========================

@dataclass
class Job:
    in_file: Path
    out_file: Path
    prompt: str

def process_one(job: Job, cfg_openai: Dict[str, Any], cfg_img: Dict[str, Any],
                conflicts: str, dry_run: bool, log_fp: Optional[io.TextIOBase], client: OpenAI):
    try:
        if dry_run:
            log_print(f"[dry-run] Сгенерировали бы для: {job.in_file.name} | prompt: {job.prompt}", log_fp)
            return True

        size = cfg_openai.get("openai_size", "1024x1024")
        n = int(cfg_openai.get("n", 1))

        resp = client.images.generate(
            model=str(cfg_openai.get("model", "gpt-image-1")),
            prompt=job.prompt,
            size=size,
            n=n
        )

        # сохраняем каждую
        for idx, data in enumerate(resp.data, start=1):
            out_path = job.out_file
            if n > 1:
                out_path = out_path.with_stem(out_path.stem + f"_{idx}")
            img_b64 = data.b64_json
            img_bytes = base64.b64decode(img_b64)
            save_image_bytes(img_bytes, out_path, cfg_img, conflicts, dry_run, log_fp)

        return True
    except Exception:
        tb = traceback.format_exc()
        log_print(f"❌ Ошибка для {job.in_file}:\n{tb}", log_fp)
        return False

def main():
    cfg = load_config()

    # Лог
    log_fp: Optional[io.TextIOBase] = None
    log_file = (cfg.get("log_file") or "").strip()
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            log_fp = open(log_file, "a", encoding="utf-8")
        except Exception as e:
            print(f"⚠️  Не удалось открыть лог-файл '{log_file}': {e}")

    dry_run = bool(cfg.get("dry_run", False))
    conflicts = str(cfg.get("conflicts", "skip"))
    workers = int(cfg.get("workers", 0))

    cfg_openai = cfg.get("openai") or {}
    cfg_img = cfg.get("image") or {}

    # OpenAI client
    api_key = (cfg_openai.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
    if not api_key and not dry_run:
        log_print("❌ Не задан API-ключ OpenAI (ни в config.toml, ни в переменной окружения OPENAI_API_KEY).", log_fp)
        if log_fp: log_fp.close()
        return
    client = OpenAI(api_key=api_key) if not dry_run else None  # type: ignore

    # Собираем входные файлы
    files = collect_text_files(cfg, log_fp)
    if not files:
        log_print("ℹ️  Текстовых файлов не найдено — делать нечего.", log_fp)
        if log_fp: log_fp.close()
        return

    # Задачи
    image_format = (cfg_img.get("format") or "png").lower()
    jobs: List[Job] = []
    for f in files:
        out = compute_output_path(f, cfg, image_format=image_format)
        prompt = build_prompt_for_file(f, cfg_openai)
        jobs.append(Job(in_file=f, out_file=out, prompt=prompt))

    log_print(f"Старт: файлов={len(jobs)} | dry_run={dry_run} | workers={workers}", log_fp)

    ok = 0
    fail = 0
    if workers and workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(process_one, j, cfg_openai, cfg_img, conflicts, dry_run, log_fp, client): j for j in jobs}
            for fut in as_completed(futs):
                ok += 1 if fut.result() else 0
        fail = len(jobs) - ok
    else:
        for j in jobs:
            ok += 1 if process_one(j, cfg_openai, cfg_img, conflicts, dry_run, log_fp, client) else 0
        fail = len(jobs) - ok

    log_print(f"Готово. Успешно: {ok} | Ошибок: {fail}", log_fp)
    if log_fp: log_fp.close()

if __name__ == "__main__":
    main()
