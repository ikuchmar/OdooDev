# -*- coding: utf-8 -*-
"""
Новая логика: ОСНОВА — ТЕКСТОВЫЕ ФАЙЛЫ.
Для каждого *.txt в указанных папках/файлах ищем соответствующие изображения в той же папке
и накладываем белый текст по настройкам.

Поддержка image_match_mode:
- "exact"  — только строго одноимённые картинки (name.txt → name.jpg/.png/.webp).
- "prefix" — все картинки, чьи имена начинаются с базового имени текста (name_1.jpg, name-final.png и т.п.).

Запуск без параметров: читает config.toml, лежащий рядом со скриптом.

Зависимости:
    pip install pillow
Требуется Python 3.11+ (для tomllib).
"""

import os
import sys
import logging
from typing import List, Tuple, Optional, Iterable
from pathlib import Path

# tomllib — стандартный модуль Python 3.11+
try:
    import tomllib
except Exception:
    print("Ошибка: требуется Python 3.11+ (для модуля tomllib).", file=sys.stderr)
    raise

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor


# =========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================

def load_config(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def setup_logging(level_name: str, log_to_file: bool, log_file: str):
    level = getattr(logging, level_name.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_to_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers
    )


def collect_texts(input_dirs: List[str], input_files: List[str]) -> List[Path]:
    """
    Собираем TXT-файлы из указанных папок (с учётом recursive в конфиге) и из явных путей.
    ВАЖНО: теперь input_dirs/input_files — это ИСТОЧНИКИ ТЕКСТОВЫХ КАРТОЧЕК.
    """
    # recursive берём из конфига прямо здесь, чтобы не плодить параметры
    # (читаем повторно из окружения — норм, либо можно пробросить аргументом)
    # Но лучше получать из already loaded config — передадим через замыкание:
    raise NotImplementedError  # будет заменено ниже


# перепишем collect_texts с доступом к cfg через параметр:
def collect_texts(input_dirs: List[str], input_files: List[str], recursive: bool) -> List[Path]:
    result: List[Path] = []

    # Из папок
    for d in input_dirs or []:
        p = Path(d)
        if not p.exists():
            logging.warning("Папка (для TXT) не найдена: %s", p)
            continue
        it = p.rglob("*.txt") if recursive else p.glob("*.txt")
        for f in it:
            if f.is_file() and f.suffix.lower() == ".txt":
                result.append(f)

    # Из явных файлов
    for f in input_files or []:
        p = Path(f)
        if p.is_file() and p.suffix.lower() == ".txt":
            result.append(p)
        else:
            logging.warning("TXT-файл не найден или имеет неверное расширение: %s", p)

    return sorted(set(result))


def parse_color(value: str) -> Tuple[int, int, int, int]:
    v = value.strip()
    if v.startswith("#") and len(v) == 9:  # #RRGGBBAA
        r = int(v[1:3], 16)
        g = int(v[3:5], 16)
        b = int(v[5:7], 16)
        a = int(v[7:9], 16)
        return (r, g, b, a)
    rgb = ImageColor.getrgb(v)
    return (rgb[0], rgb[1], rgb[2], 255)


def compute_anchor_xy(anchor: str, img_w: int, img_h: int, box_w: int, box_h: int, margin_x: int, margin_y: int) -> Tuple[int, int]:
    x = (img_w - box_w) // 2
    y = (img_h - box_h) // 2
    a = anchor.lower()

    if "top" in a:
        y = margin_y
    elif "bottom" in a:
        y = img_h - box_h - margin_y

    if a.endswith("left"):
        x = margin_x
    elif a.endswith("right"):
        x = img_w - box_w - margin_x
    elif a.endswith("center"):
        x = (img_w - box_w) // 2

    return x, y


def wrap_text_to_width(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int) -> List[str]:
    lines: List[str] = []
    for raw_line in text.splitlines():
        # сохраняем пустые строки
        if raw_line.strip() == "" and raw_line != "":
            lines.append("")  # была именно пустая строка (напр. разделитель абзацев)
            continue

        words = raw_line.split(" ")
        if not words:
            lines.append("")
            continue

        current = ""
        for w in words:
            candidate = (current + " " + w).strip() if current else w
            bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=0)
            width = bbox[2] - bbox[0]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = w
        if current != "":
            lines.append(current)

    return lines


def text_block_bbox(lines: List[str], font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, line_spacing: float, stroke_width: int) -> Tuple[int, int]:
    max_w = 0
    total_h = 0
    prev_h = 0
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line if line else " ", font=font, stroke_width=stroke_width)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_w = max(max_w, w)
        if i == 0:
            total_h += h
        else:
            total_h += int(prev_h * line_spacing)
        prev_h = h
    return max_w, total_h


def draw_multiline_text(
    img: Image.Image,
    xy: Tuple[int, int],
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int, int],
    align: str,
    line_spacing: float,
    readability_style: str,
    stroke_width: int,
    stroke_fill: Tuple[int, int, int, int],
    background_box_fill: Tuple[int, int, int, int],
):
    draw = ImageDraw.Draw(img, "RGBA")
    bw, bh = text_block_bbox(lines, font, draw, line_spacing, stroke_width=stroke_width)
    x, y = xy

    # Подложка
    if readability_style in ("box", "both"):
        box = Image.new("RGBA", (bw, bh), background_box_fill)
        img.alpha_composite(box, dest=(x, y))

    # Рисуем строки с учётом выравнивания
    # align: left/center/right
    prev_h = 0
    ly = y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line if line else " ", font=font, stroke_width=stroke_width)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]

        if i == 0:
            ly = y
        else:
            ly = ly + int(prev_h * line_spacing)
        prev_h = lh

        if align == "left":
            lx = x
        elif align == "right":
            lx = x + (bw - lw)
        else:  # center
            lx = x + (bw - lw) // 2

        draw.text(
            (lx, ly),
            line,
            font=font,
            fill=color,
            stroke_width=stroke_width if readability_style in ("stroke", "both") else 0,
            stroke_fill=stroke_fill
        )


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def normalize_format_and_ext(src: Path, save_format_cfg: str) -> Tuple[str, str]:
    if save_format_cfg:
        fmt = save_format_cfg.upper()
        if fmt not in ("JPEG", "PNG", "WEBP"):
            logging.warning("Неподдерживаемый save_format '%s'. Используем формат исходника.", fmt)
        else:
            return (fmt, ".jpg" if fmt == "JPEG" else ".png" if fmt == "PNG" else ".webp")

    ext = src.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "JPEG", ".jpg"
    if ext == ".png":
        return "PNG", ".png"
    if ext == ".webp":
        return "WEBP", ".webp"

    logging.warning("Неожиданное расширение '%s' у %s. Сохраняем как PNG.", ext, src.name)
    return "PNG", ".png"


def choose_output_path(src_img: Path, output_dir: str, naming: str, suffix: str, save_ext: str) -> Optional[Path]:
    if naming not in ("suffix", "overwrite", "skip_if_exists"):
        logging.warning("Неизвестный режим output_naming: %s, используем 'suffix'", naming)
        naming = "suffix"

    if output_dir:
        base = Path(output_dir) / src_img.name
        if naming == "suffix":
            base = base.with_stem(base.stem + suffix)
        out_path = base.with_suffix(save_ext)
        ensure_dir(out_path.parent)
        if naming == "skip_if_exists" and out_path.exists():
            return None
        return out_path

    if naming == "overwrite":
        return src_img.with_suffix(save_ext)
    elif naming == "skip_if_exists":
        candidate = src_img.with_suffix(save_ext)
        return None if candidate.exists() else candidate
    else:
        return src_img.with_stem(src_img.stem + suffix).with_suffix(save_ext)


def find_images_for_text(
    txt_path: Path,
    image_exts: Iterable[str],
    match_mode: str
) -> List[Path]:
    """
    Ищем картинки для данного txt в его папке.
    - exact: только basename совпадает.
    - prefix: имя картинки начинается с basename текста.
    Сравнение — регистронезависимое по stem.
    """
    folder = txt_path.parent
    if not folder.exists():
        return []

    base = txt_path.stem.lower()
    exts = set(e.lower() for e in image_exts)

    candidates: List[Path] = []
    for f in folder.iterdir():
        if not f.is_file():
            continue
        if f.suffix.lower() not in exts:
            continue
        name_no_ext_lower = f.stem.lower()

        if match_mode == "exact":
            if name_no_ext_lower == base:
                candidates.append(f)
        else:  # prefix
            if name_no_ext_lower.startswith(base):
                candidates.append(f)

    return sorted(candidates)


def process_one_image(
    img_path: Path,
    text: str,
    cfg: dict,
    dry_run: bool
) -> bool:
    try:
        img = Image.open(img_path)
        if cfg.get("respect_exif_orientation", True):
            img = ImageOps.exif_transpose(img)
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        W, H = img.size
        max_w = int(W * float(cfg.get("max_width_pct", 0.9)))
        max_h = int(H * float(cfg.get("max_height_pct", 0.5)))
        margin_x = int(cfg.get("margin_x", 32))
        margin_y = int(cfg.get("margin_y", 32))
        anchor = str(cfg.get("anchor", "bottom_center")).lower()
        align = str(cfg.get("align", "center")).lower()
        line_spacing = float(cfg.get("line_spacing", 1.2))

        readability_style = str(cfg.get("readability_style", "both")).lower()
        stroke_width = int(cfg.get("stroke_width", 2))
        stroke_fill = parse_color(cfg.get("stroke_fill", "#000000"))
        background_box_fill = parse_color(cfg.get("background_box_fill", "#00000080"))
        text_color = parse_color(cfg.get("color", "#FFFFFF"))

        font_path = cfg.get("font_path")
        if not font_path or not Path(font_path).is_file():
            logging.error("Не найден font_path: %r. Укажите корректный путь к шрифту в config.toml", font_path)
            return False

        min_font_size = int(cfg.get("min_font_size", 14))
        font_size_cfg = cfg.get("font_size", "auto")

        draw = ImageDraw.Draw(img, "RGBA")

        # Подбор размера
        if isinstance(font_size_cfg, int):
            font_size = int(font_size_cfg)
        else:
            font_size = max(int(H * 0.07), min_font_size)

        font = ImageFont.truetype(font_path, font_size)
        wrapped = wrap_text_to_width(text, font, draw, max_w)
        bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

        while bh > max_h and font_size > min_font_size:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
            wrapped = wrap_text_to_width(text, font, draw, max_w)
            bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

        if bh > max_h and font_size == min_font_size:
            logging.warning("[%s] Текст не помещается в max_height_pct при min_font_size=%d. Будет усечён.",
                            img_path.name, min_font_size)
            while wrapped and text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)[1] > max_h:
                wrapped = wrapped[:-1]
            if wrapped:
                wrapped[-1] = (wrapped[-1] + "…").rstrip()
            bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

        box_w = min(bw, max_w)
        box_h = min(bh, max_h)
        x, y = compute_anchor_xy(anchor, W, H, box_w, box_h, margin_x, margin_y)

        if dry_run:
            logging.info("[DRY RUN] %s → %d строк, шрифт=%d, блок=%dx%d, якорь=%s",
                         img_path.name, len(wrapped), font_size, box_w, box_h, anchor)
            return True

        draw_multiline_text(
            img=img,
            xy=(x, y),
            lines=wrapped,
            font=font,
            color=text_color,
            align=align,
            line_spacing=line_spacing,
            readability_style=readability_style,
            stroke_width=stroke_width,
            stroke_fill=stroke_fill,
            background_box_fill=background_box_fill,
        )

        save_format, save_ext = normalize_format_and_ext(img_path, cfg.get("save_format", ""))
        out_path = choose_output_path(
            src_img=img_path,
            output_dir=cfg.get("output_dir", ""),
            naming=cfg.get("output_naming", "suffix"),
            suffix=cfg.get("output_suffix", "_with_text"),
            save_ext=save_ext,
        )

        if out_path is None:
            logging.info("Пропуск сохранения (skip_if_exists): %s", img_path.name)
            return True

        params = {}
        img_to_save = img
        if save_format == "JPEG":
            params["quality"] = int(cfg.get("jpeg_quality", 90))
            params["subsampling"] = "4:2:0"
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img_to_save = bg
            else:
                img_to_save = img.convert("RGB")
        elif save_format == "WEBP":
            params["quality"] = int(cfg.get("webp_quality", 90))

        ensure_dir(out_path.parent)
        img_to_save.save(out_path, format=save_format, **params)
        logging.info("Сохранено: %s", out_path)
        return True

    except Exception as e:
        logging.exception("Ошибка при обработке изображения %s: %s", img_path, e)
        return False


# ==========
# ОСНОВА
# ==========

def main():
    cfg_path = Path(__file__).with_name("config.toml")
    if not cfg_path.exists():
        print("Не найден config.toml рядом со скриптом.", file=sys.stderr)
        sys.exit(2)

    cfg = load_config(cfg_path)

    setup_logging(
        level_name=cfg.get("logging_level", "INFO"),
        log_to_file=bool(cfg.get("log_to_file", False)),
        log_file=str(cfg.get("log_file", "overlay.log")),
    )

    logging.info("Старт. Конфиг: %s", cfg_path)

    recursive = bool(cfg.get("recursive", True))
    text_files = collect_texts(
        input_dirs=cfg.get("input_dirs", []),
        input_files=cfg.get("input_files", []),
        recursive=recursive
    )

    if not text_files:
        logging.warning("TXT-файлы не найдены по заданным путям.")
        return

    image_exts = [e.lower() for e in cfg.get("image_extensions", [".jpg", ".jpeg", ".png", ".webp"])]
    text_encoding = cfg.get("text_encoding", "utf-8")
    dry_run = bool(cfg.get("dry_run", False))

    match_mode = str(cfg.get("image_match_mode", "prefix")).lower()
    if match_mode not in ("exact", "prefix"):
        logging.warning("Неизвестный image_match_mode: %s — используем 'prefix'", match_mode)
        match_mode = "prefix"

    total_txt = len(text_files)
    total_images = 0
    processed = 0
    skipped = 0
    no_images = 0

    for txt in text_files:
        try:
            text = txt.read_text(encoding=text_encoding)
        except Exception as e:
            logging.error("Не удалось прочитать текст %s: %s", txt, e)
            skipped += 1
            continue

        images = find_images_for_text(txt, image_exts, match_mode=match_mode)
        if not images:
            no_images += 1
            logging.info("Нет подходящих картинок для %s — пропуск.", txt.name)
            continue

        total_images += len(images)
        for img_path in images:
            ok = process_one_image(img_path, text, cfg, dry_run=dry_run)
            if ok:
                processed += 1
            else:
                skipped += 1

    logging.info(
        "Готово. TXT: %d; найдено картинок: %d; успешно обработано: %d; без картинок: %d; ошибок: %d",
        total_txt, total_images, processed, no_images, skipped
    )


if __name__ == "__main__":
    main()
