# -*- coding: utf-8 -*-
"""
Скрипт накладывает текст (из одноимённых .txt-файлов) на изображения.
- Запуск без параметров: читает config.toml из текущего каталога.
- Для каждого изображения ищется файл <имя>.txt в той же папке.
- Если текст не найден — изображение пропускается.
- Текст накладывается белым цветом; улучшение читабельности — контур и/или подложка (по настройке).
- Шрифт обязателен (font_path в конфиге). Есть автоподбор размера с минимальным порогом.
- Результаты сохраняются в output_dir или рядом с исходником (по конфигу).
"""

import os
import sys
import logging
from typing import List, Tuple, Optional
from pathlib import Path

# tomllib — стандартный модуль Python 3.11+
try:
    import tomllib
except Exception as e:
    print("Ошибка: требуется Python 3.11+ (модуль tomllib).", file=sys.stderr)
    raise

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor

# -----------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# -----------------------------

def load_config(path: Path) -> dict:
    """Читает TOML-конфиг и возвращает словарь настроек."""
    with path.open("rb") as f:
        return tomllib.load(f)


def setup_logging(level_name: str, log_to_file: bool, log_file: str):
    """Настройка логирования в консоль и (опционально) в файл."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_to_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers
    )


def collect_images(input_dirs: List[str], input_files: List[str], recursive: bool, exts: List[str]) -> List[Path]:
    """
    Сбор изображений из папок и явных путей.
    exts — список расширений (в нижнем регистре, с точкой).
    """
    result = []
    # Из папок
    for d in input_dirs or []:
        p = Path(d)
        if not p.exists():
            logging.warning("Папка не найдена: %s", p)
            continue
        if recursive:
            it = p.rglob("*")
        else:
            it = p.glob("*")
        for f in it:
            if f.is_file() and f.suffix.lower() in exts:
                result.append(f)
    # Из явных файлов
    for f in input_files or []:
        p = Path(f)
        if p.is_file() and p.suffix.lower() in exts:
            result.append(p)
        else:
            logging.warning("Файл не найден или неподдерживаемый формат: %s", p)
    # Убираем дубликаты и сортируем
    uniq = sorted(set(result))
    return uniq


def read_text_pair(image_path: Path, text_ext: str, encoding: str) -> Optional[str]:
    """Читает текст из одноимённого файла (<stem><text_ext>) в той же папке. Если нет — возвращает None."""
    txt_path = image_path.with_suffix(text_ext)
    if not txt_path.exists():
        return None
    try:
        return txt_path.read_text(encoding=encoding)
    except Exception as e:
        logging.error("Не удалось прочитать текст %s: %s", txt_path, e)
        return None


def parse_color(value: str) -> Tuple[int, int, int, int]:
    """
    Парсит цвет в #RRGGBB или #RRGGBBAA в RGBA-кортеж.
    Если указан #RRGGBB — альфа=255
    """
    # PIL.ImageColor.getrgb возвращает RGB. Для RGBA используем свой разбор.
    v = value.strip()
    if v.startswith("#") and len(v) == 9:  # #RRGGBBAA
        r = int(v[1:3], 16)
        g = int(v[3:5], 16)
        b = int(v[5:7], 16)
        a = int(v[7:9], 16)
        return (r, g, b, a)
    # Иначе RGB
    rgb = ImageColor.getrgb(v)
    return (rgb[0], rgb[1], rgb[2], 255)


def compute_anchor_xy(anchor: str, img_w: int, img_h: int, box_w: int, box_h: int, margin_x: int, margin_y: int) -> Tuple[int, int]:
    """
    Возвращает координату левого-верхнего угла области под текст (box_w x box_h),
    исходя из якоря и отступов.
    """
    # По умолчанию — центр
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


def wrap_text_to_width(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_width: int, align: str) -> List[str]:
    """
    Перенос строк по ширине max_width. Сохраняет пустые строки.
    """
    lines = []
    for raw_line in text.splitlines():
        words = raw_line.split(" ")
        if not words:
            lines.append("")  # пустая строка
            continue
        current = ""
        for w in words:
            candidate = (current + " " + w).strip() if current else w
            # bbox = draw.textbbox((0,0), candidate, font=font)  # нет align влияния на ширину
            bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=0)
            width = bbox[2] - bbox[0]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = w
        if current != "":
            lines.append(current)
        # Если строка была вовсе пустая — уже добавили выше.
    return lines


def text_block_bbox(lines: List[str], font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, line_spacing: float, stroke_width: int) -> Tuple[int, int]:
    """
    Возвращает (width, height) многострочного блока с учётом межстрочного интервала и контура.
    """
    max_w = 0
    total_h = 0
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line if line else " ", font=font, stroke_width=stroke_width)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_w = max(max_w, w)
        if i == 0:
            total_h += h
        else:
            total_h += int(h * line_spacing)
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
    """
    Рисует многострочный текст построчно с выравниванием align и опциональной подложкой/контуром.
    """
    draw = ImageDraw.Draw(img, "RGBA")

    # Сначала рассчитываем общий bbox
    bw, bh = text_block_bbox(lines, font, draw, line_spacing, stroke_width=stroke_width)

    # Подложка под текст — прямоугольник ровно по блоку
    x, y = xy

    if readability_style in ("box", "both"):
        box = Image.new("RGBA", (bw, bh), background_box_fill)
        img.alpha_composite(box, dest=(x, y))

    # Рисуем строки
    # Выравнивание по горизонтали
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line if line else " ", font=font, stroke_width=stroke_width)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]

        # Горизонтальная позиция строки
        if align == "left":
            lx = x
        elif align == "right":
            lx = x + (bw - lw)
        else:  # center
            lx = x + (bw - lw) // 2

        if i == 0:
            ly = y
        else:
            # шаг вниз: высота строки * line_spacing
            prev_bbox = draw.textbbox((0, 0), lines[i-1] if lines[i-1] else " ", font=font, stroke_width=stroke_width)
            prev_h = prev_bbox[3] - prev_bbox[1]
            ly = ly + int(prev_h * line_spacing)

        # stroke (контур) рисуется параметрами stroke_width/stroke_fill
        draw.text((lx, ly), line, font=font, fill=color,
                  stroke_width=stroke_width if readability_style in ("stroke", "both") else 0,
                  stroke_fill=stroke_fill)


def ensure_dir(path: Path):
    """Создаёт папку при необходимости."""
    path.mkdir(parents=True, exist_ok=True)


def choose_output_path(src_img: Path, output_dir: str, naming: str, suffix: str, save_ext: str) -> Optional[Path]:
    """
    Возвращает путь к выходному файлу в зависимости от схемы именования.
    save_ext — расширение с точкой (например, ".jpg"), согласованное с форматом сохранения.
    """
    if naming not in ("suffix", "overwrite", "skip_if_exists"):
        logging.warning("Неизвестный режим output_naming: %s, используем 'suffix'", naming)
        naming = "suffix"

    if output_dir:
        out_base = Path(output_dir) / src_img.name
        if naming == "suffix":
            out_base = out_base.with_stem(out_base.stem + suffix)
        out_path = out_base.with_suffix(save_ext)
        ensure_dir(out_path.parent)
        if naming == "skip_if_exists" and out_path.exists():
            return None
        return out_path

    # Сохраняем рядом
    if naming == "overwrite":
        return src_img.with_suffix(save_ext)
    elif naming == "skip_if_exists":
        # Если уже существует файл с той же схемой (рядом с исходником)
        candidate = src_img.with_suffix(save_ext)
        return None if candidate.exists() else candidate
    else:  # suffix
        candidate = src_img.with_stem(src_img.stem + suffix).with_suffix(save_ext)
        return candidate


def normalize_format_and_ext(src: Path, save_format_cfg: str) -> Tuple[str, str]:
    """
    Определяет формат сохранения (PIL format) и расширение файла.
    save_format_cfg: "" => как у исходника.
    Возвращает (save_format, save_ext).
    """
    if save_format_cfg:
        fmt = save_format_cfg.upper()
        if fmt not in ("JPEG", "PNG", "WEBP"):
            logging.warning("Неподдерживаемый save_format '%s'. Используем формат исходника.", fmt)
            save_format_cfg = ""
        else:
            if fmt == "JPEG":
                return "JPEG", ".jpg"
            elif fmt == "PNG":
                return "PNG", ".png"
            else:
                return "WEBP", ".webp"

    # Как у исходника
    ext = src.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "JPEG", ".jpg"
    elif ext == ".png":
        return "PNG", ".png"
    elif ext == ".webp":
        return "WEBP", ".webp"
    else:
        # По умолчанию — PNG
        logging.warning("Неизвестное расширение '%s' у %s. Сохраняем как PNG.", ext, src.name)
        return "PNG", ".png"


def process_one(
    img_path: Path,
    text: str,
    cfg: dict,
    dry_run: bool = False,
) -> bool:
    """
    Обработка одного изображения. Возвращает True, если успешно.
    """
    try:
        # Загружаем и учитываем EXIF-ориентацию
        img = Image.open(img_path)
        if cfg.get("respect_exif_orientation", True):
            img = ImageOps.exif_transpose(img)

        # Гарантируем RGBA для подложки
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        W, H = img.size

        # Параметры области
        max_w = int(W * float(cfg.get("max_width_pct", 0.9)))
        max_h = int(H * float(cfg.get("max_height_pct", 0.5)))
        margin_x = int(cfg.get("margin_x", 32))
        margin_y = int(cfg.get("margin_y", 32))
        anchor = str(cfg.get("anchor", "bottom_center")).lower()
        align = str(cfg.get("align", "center")).lower()
        line_spacing = float(cfg.get("line_spacing", 1.2))

        # Читаем стиль
        readability_style = str(cfg.get("readability_style", "both")).lower()
        stroke_width = int(cfg.get("stroke_width", 2))
        stroke_fill = parse_color(cfg.get("stroke_fill", "#000000"))
        background_box_fill = parse_color(cfg.get("background_box_fill", "#00000080"))
        text_color = parse_color(cfg.get("color", "#FFFFFF"))

        # Шрифт
        font_path = cfg.get("font_path")
        if not font_path or not Path(font_path).is_file():
            logging.error("Не найден font_path: %r. Укажите корректный путь к шрифту в config.toml", font_path)
            return False

        font_size_cfg = cfg.get("font_size", "auto")
        min_font_size = int(cfg.get("min_font_size", 14))

        draw = ImageDraw.Draw(img, "RGBA")

        # Подбор размера шрифта
        if isinstance(font_size_cfg, int):
            font_size = int(font_size_cfg)
            font = ImageFont.truetype(font_path, font_size)
            wrapped = wrap_text_to_width(text, font, draw, max_w, align)
            bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)
            # Если блок выше max_h — уменьшаем до min_font_size
            while bh > max_h and font_size > min_font_size:
                font_size -= 1
                font = ImageFont.truetype(font_path, font_size)
                wrapped = wrap_text_to_width(text, font, draw, max_w, align)
                bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)
        else:
            # "auto" — начинаем с разумного базового размера как функция высоты изображения
            # Простейшая эвристика: 7% высоты
            font_size = max(int(H * 0.07), min_font_size)
            font = ImageFont.truetype(font_path, font_size)
            wrapped = wrap_text_to_width(text, font, draw, max_w, align)
            bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)
            # Уменьшаем, пока не влезет по высоте или пока не достигнем min_font_size
            while bh > max_h and font_size > min_font_size:
                font_size -= 1
                font = ImageFont.truetype(font_path, font_size)
                wrapped = wrap_text_to_width(text, font, draw, max_w, align)
                bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)

        # Если всё ещё не помещается по высоте на минимальном размере — предупредим
        if bh > max_h and font_size == min_font_size:
            logging.warning("Текст не помещается в отведённую высоту даже при min_font_size=%d. Будет усечён.", min_font_size)
            # Грубое усечение: уменьшаем число строк, пока не влезет
            while wrapped and text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)[1] > max_h:
                wrapped = wrapped[:-1]
            if wrapped:
                # Добавим троеточие к последней строке
                wrapped[-1] = (wrapped[-1] + "…").rstrip()

            bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width=stroke_width)

        # Координаты области (по фактическому блоку, но ограничим максимальной шириной)
        # Чтобы якорь выставлялся по рамке текста, используем box_w=bw, box_h=bh
        box_w = min(bw, max_w)
        box_h = min(bh, max_h)
        x, y = compute_anchor_xy(anchor, W, H, box_w, box_h, margin_x, margin_y)

        if dry_run:
            logging.info("[DRY RUN] Наложение текста на %s: %d строк, шрифт=%d, блок=%dx%d, якорь=%s",
                         img_path.name, len(wrapped), font_size, box_w, box_h, anchor)
            return True

        # Рисуем текст
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

        # Определяем выходной путь
        save_format, save_ext = normalize_format_and_ext(img_path, cfg.get("save_format", ""))
        out_path = choose_output_path(
            src_img=img_path,
            output_dir=cfg.get("output_dir", ""),
            naming=cfg.get("output_naming", "suffix"),
            suffix=cfg.get("output_suffix", "_with_text"),
            save_ext=save_ext,
        )

        if out_path is None:
            logging.info("Пропуск сохранения (skip_if_exists) для %s", img_path.name)
            return True

        params = {}
        if save_format == "JPEG":
            params["quality"] = int(cfg.get("jpeg_quality", 90))
            params["subsampling"] = "4:2:0"
            # JPEG не поддерживает альфа — склеим на белом фоне
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img_to_save = bg
            else:
                img_to_save = img.convert("RGB")
        elif save_format == "WEBP":
            params["quality"] = int(cfg.get("webp_quality", 90))
            img_to_save = img
        else:
            img_to_save = img

        ensure_dir(out_path.parent)
        img_to_save.save(out_path, format=save_format, **params)
        logging.info("Сохранено: %s", out_path)
        return True

    except Exception as e:
        logging.exception("Ошибка при обработке %s: %s", img_path, e)
        return False


def main():
    # Путь к конфигу
    cfg_path = Path(__file__).with_name("config.toml")
    if not cfg_path.exists():
        print("Не найден config.toml рядом со скриптом. Создайте файл настроек.", file=sys.stderr)
        sys.exit(2)

    cfg = load_config(cfg_path)

    # Логи
    setup_logging(
        level_name=cfg.get("logging_level", "INFO"),
        log_to_file=bool(cfg.get("log_to_file", False)),
        log_file=str(cfg.get("log_file", "overlay.log"))
    )

    logging.info("Старт обработки. Конфиг: %s", cfg_path)

    # Сбор изображений
    images = collect_images(
        input_dirs=cfg.get("input_dirs", []),
        input_files=cfg.get("input_files", []),
        recursive=bool(cfg.get("recursive", True)),
        exts=[e.lower() for e in cfg.get("image_extensions", [".jpg", ".jpeg", ".png", ".webp"])]
    )

    if not images:
        logging.warning("Не найдено изображений по заданным путям.")
        return

    dry_run = bool(cfg.get("dry_run", False))
    text_ext = cfg.get("text_extension", ".txt")
    text_encoding = cfg.get("text_encoding", "utf-8")

    total = len(images)
    ok = 0
    skipped = 0
    no_pair = 0
    for img_path in images:
        txt = read_text_pair(img_path, text_ext=text_ext, encoding=text_encoding)
        if txt is None:
            no_pair += 1
            logging.info("Нет пары .txt — пропуск: %s", img_path.name)
            continue
        success = process_one(img_path, txt, cfg, dry_run=dry_run)
        if success:
            ok += 1
        else:
            skipped += 1

    logging.info("Готово. Найдено изображений: %d; обработано: %d; без пары: %d; ошибок: %d",
                 total, ok, no_pair, skipped)


if __name__ == "__main__":
    main()
