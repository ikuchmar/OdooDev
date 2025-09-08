# -*- coding: utf-8 -*-
"""
ОСНОВА — ТЕКСТОВЫЕ ФАЙЛЫ (*.txt).
Для каждого TXT в указанных папках/файлах ищем соответствующие изображения в той же папке
и наносим текст по двум режимам:
- per_image_text_mode = "full_text": каждая выбранная картинка получает ВЕСЬ текст.
- per_image_text_mode = "line_by_line_cycle": текст режется на строки/блоки строк; блоки раздаются по картинкам циклично.
  Можно задать lines_per_image (сколько строк на одну картинку).

Поддержка image_match_mode:
- "exact"  — только строго одноимённые картинки (name.txt → name.jpg/.png/.webp).
- "prefix" — все картинки, чьи имена начинаются с базового имени текста (name_1.jpg, name-final.png и т.п.).

Фильтрация маркеров:
- remove_markers: список подстрок, которые вырезаются из текста перед обработкой.
- drop_lines_with_markers: если True — строки, содержащие любой маркер, полностью исключаются.

Индексация вывода при циклическом использовании одной картинки:
- cycle_output_indexing = true/false
- cycle_index_start, cycle_index_pad
- cycle_index_name_template = "{stem}_{i}{suffix}{ext}"

Дополнительно:
- target_images = "all" | "first" — выбирать все или только первую картинку.
- delete_original_after_success = true/false — удалять ли исходник после успешного сохранения результата
  (только если создан отдельный файл, не overwrite, и не dry_run).

Зависимости:
    pip install pillow
Требуется Python 3.11+ (для tomllib).
"""

import sys
import logging
from typing import List, Tuple, Optional, Iterable, Dict
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


def collect_texts(input_dirs: List[str], input_files: List[str], recursive: bool) -> List[Path]:
    """Собираем TXT-файлы из указанных папок (учитывая recursive) и из явных путей."""
    result: List[Path] = []

    for d in input_dirs or []:
        p = Path(d)
        if not p.exists():
            logging.warning("Папка (для TXT) не найдена: %s", p)
            continue
        it = p.rglob("*.txt") if recursive else p.glob("*.txt")
        for f in it:
            if f.is_file() and f.suffix.lower() == ".txt":
                result.append(f)

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
    """Координаты верхнего-левого угла рамки текста (box_w x box_h) по якорю и отступам."""
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
    """Перенос строк по ширине для МНОГОСТРОЧНОГО блока (режим full_text/мультистрочный)."""
    lines: List[str] = []
    for raw_line in text.splitlines():
        # Сохраняем пустые строки (если строка реально пустая)
        if raw_line.strip() == "" and raw_line != "":
            lines.append("")
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
    """Рисует многострочный блок текста с подложкой/контуром (если включены)."""
    draw = ImageDraw.Draw(img, "RGBA")
    bw, bh = text_block_bbox(lines, font, draw, line_spacing, stroke_width=stroke_width)
    x, y = xy

    if readability_style in ("box", "both"):
        box = Image.new("RGBA", (bw, bh), background_box_fill)
        img.alpha_composite(box, dest=(x, y))

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
        else:
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
    """Определяет формат сохранения (PIL) и расширение файла."""
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


def choose_output_path(
    src_img: Path,
    output_dir: str,
    naming: str,
    suffix: str,
    save_ext: str,
    *,
    index: Optional[int] = None,
    cycle_indexing: bool = False,
    cycle_index_start: int = 1,
    cycle_index_pad: int = 0,
    cycle_tpl: str = "{stem}_{i}{suffix}{ext}",
) -> Optional[Path]:
    """
    Возвращает путь к выходному файлу.
    Если передан index и cycle_indexing=True — используется индексированный шаблон имени.
    При naming='suffix' и suffix='' путь может совпасть с исходным (фактический overwrite).
    """
    if naming not in ("suffix", "overwrite", "skip_if_exists"):
        logging.warning("Неизвестный режим output_naming: %s, используем 'suffix'", naming)
        naming = "suffix"

    stem = src_img.stem
    ext = save_ext  # нормализованное расширение (".jpg"/".png"/".webp")

    def build_name_with_suffix(base_stem: str) -> str:
        return (base_stem + suffix) if naming == "suffix" else base_stem

    # Индексированная ветка (для циклов)
    if cycle_indexing and index is not None:
        i_val = max(index, cycle_index_start)
        i_str = str(i_val).zfill(max(0, cycle_index_pad))
        out_stem = cycle_tpl.format(
            stem=stem,
            i=i_str,
            suffix=(suffix if naming == "suffix" else ""),
            ext=""  # добавим отдельно
        )
        filename = out_stem + ext
        out_path = Path(output_dir, filename) if output_dir else src_img.with_name(filename)
        ensure_dir(out_path.parent)
        if naming == "skip_if_exists" and out_path.exists():
            return None
        return out_path

    # Обычная ветка
    if output_dir:
        base = Path(output_dir) / src_img.name
        if naming == "suffix":
            if suffix == "":
                logging.warning("output_naming='suffix' и output_suffix='' → фактически overwrite для %s", src_img.name)
            base = base.with_stem(build_name_with_suffix(base.stem))
        out_path = base.with_suffix(ext)
        ensure_dir(out_path.parent)
        if naming == "skip_if_exists" and out_path.exists():
            return None
        return out_path

    if naming == "overwrite":
        return src_img.with_suffix(ext)
    elif naming == "skip_if_exists":
        candidate = src_img.with_suffix(ext)
        return None if candidate.exists() else candidate
    else:
        if suffix == "":
            logging.warning("output_naming='suffix' и output_suffix='' → фактически overwrite для %s", src_img.name)
        return src_img.with_stem(build_name_with_suffix(src_img.stem)).with_suffix(ext)


def find_images_for_text(
    txt_path: Path,
    image_exts: Iterable[str],
    match_mode: str
) -> List[Path]:
    """
    Ищем картинки для данного TXT в его папке.
    - exact: только basename совпадает.
    - prefix: имя картинки начинается с basename текста.
    Сравнение регистронезависимое по stem.
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


# =========================
# ФИЛЬТРАЦИЯ ТЕКСТА ПО МАРКЕРАМ
# =========================

def filter_text_by_markers_raw(text: str, markers: List[str], drop_lines: bool) -> str:
    """
    Фильтрует сырой текст (целиком):
    - drop_lines=True: строки с любым маркером удаляются целиком.
    - drop_lines=False: маркеры вырезаются как подстроки.
    """
    if not markers:
        return text

    if drop_lines:
        kept_lines: List[str] = []
        for line in text.splitlines():
            if any(m in line for m in markers):
                continue
            kept_lines.append(line)
        return "\n".join(kept_lines)

    cleaned = text
    for m in markers:
        if m:
            cleaned = cleaned.replace(m, "")
    return cleaned


def filter_lines_by_markers(lines: List[str], markers: List[str], drop_lines: bool) -> List[str]:
    """
    Фильтрует список строк:
    - drop_lines=True: удаляет строки, содержащие любой маркер.
    - drop_lines=False: вырезает маркеры как подстроки в каждой строке.
    """
    if not markers:
        return lines

    if drop_lines:
        return [ln for ln in lines if not any(m in ln for m in markers)]

    cleaned: List[str] = []
    for ln in lines:
        for m in markers:
            if m:
                ln = ln.replace(m, "")
        cleaned.append(ln)
    return cleaned


# =========================
# РЕНДЕРИНГ
# =========================

def fit_single_line_to_box(text_line: str, font_path: str, font_size: int, min_font_size: int,
                           draw: ImageDraw.ImageDraw, max_w: int, max_h: int,
                           stroke_width: int) -> Tuple[ImageFont.FreeTypeFont, str, int, int]:
    """
    Подгоняет ОДНУ строку под ограничение (max_w, max_h), уменьшая шрифт до min_font_size.
    Если всё ещё не влезает — усечёт с '…'.
    Возвращает (font, possibly_trimmed_line, bw, bh).
    """
    size = font_size
    font = ImageFont.truetype(font_path, size)

    def line_bbox(line: str) -> Tuple[int, int]:
        bb = draw.textbbox((0, 0), line if line else " ", font=font, stroke_width=stroke_width)
        return (bb[2] - bb[0], bb[3] - bb[1])

    bw, bh = line_bbox(text_line)
    while (bw > max_w or bh > max_h) and size > min_font_size:
        size -= 1
        font = ImageFont.truetype(font_path, size)
        bw, bh = line_bbox(text_line)

    if bw > max_w:
        ell = "…"
        base = text_line
        while base and (draw.textbbox((0, 0), base + ell, font=font, stroke_width=stroke_width)[2] > max_w):
            base = base[:-1]
        text_line = (base + ell) if base else ell
        bb = draw.textbbox((0, 0), text_line, font=font, stroke_width=stroke_width)
        bw = bb[2] - bb[0]
        bh = bb[3] - bb[1]

    return font, text_line, bw, bh


def render_text_block_on_image(
    img: Image.Image,
    text_lines: List[str],
    cfg: dict,
) -> Image.Image:
    """Рендерит МНОГОСТРОЧНЫЙ блок (full_text или line_by_line_cycle с lines_per_image>1)."""
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
        raise FileNotFoundError(f"font_path не найден: {font_path}")

    min_font_size = int(cfg.get("min_font_size", 14))
    font_size_cfg = cfg.get("font_size", "auto")

    draw = ImageDraw.Draw(img, "RGBA")

    if isinstance(font_size_cfg, int):
        font_size = int(font_size_cfg)
    else:
        font_size = max(int(H * 0.07), min_font_size)

    font = ImageFont.truetype(font_path, font_size)

    wrapped = wrap_text_to_width("\n".join(text_lines), font, draw, max_w)
    bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

    while bh > max_h and font_size > min_font_size:
        font_size -= 1
        font = ImageFont.truetype(font_path, font_size)
        wrapped = wrap_text_to_width("\n".join(text_lines), font, draw, max_w)
        bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

    if bh > max_h and font_size == min_font_size:
        logging.warning("Текст-блок не помещается даже при min_font_size=%d. Будет усечён.", min_font_size)
        while wrapped and text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)[1] > max_h:
            wrapped = wrapped[:-1]
        if wrapped:
            wrapped[-1] = (wrapped[-1] + "…").rstrip()
        bw, bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

    box_w = min(bw, max_w)
    box_h = min(bh, max_h)
    x, y = compute_anchor_xy(anchor, W, H, box_w, box_h, margin_x, margin_y)

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
    return img


def render_single_line_on_image(
    img: Image.Image,
    line: str,
    cfg: dict,
) -> Image.Image:
    """Рендерит ОДНУ строку (используется при lines_per_image=1)."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    W, H = img.size

    max_w = int(W * float(cfg.get("max_width_pct", 0.9)))
    max_h = int(H * float(cfg.get("max_height_pct", 0.5)))
    margin_x = int(cfg.get("margin_x", 32))
    margin_y = int(cfg.get("margin_y", 32))
    anchor = str(cfg.get("anchor", "bottom_center")).lower()

    readability_style = str(cfg.get("readability_style", "both")).lower()
    stroke_width = int(cfg.get("stroke_width", 2))
    stroke_fill = parse_color(cfg.get("stroke_fill", "#000000"))
    background_box_fill = parse_color(cfg.get("background_box_fill", "#00000080"))
    text_color = parse_color(cfg.get("color", "#FFFFFF"))

    font_path = cfg.get("font_path")
    if not font_path or not Path(font_path).is_file():
        raise FileNotFoundError(f"font_path не найден: {font_path}")

    min_font_size = int(cfg.get("min_font_size", 14))
    font_size_cfg = cfg.get("font_size", "auto")

    draw = ImageDraw.Draw(img, "RGBA")

    if isinstance(font_size_cfg, int):
        base_size = int(font_size_cfg)
    else:
        base_size = max(int(H * 0.07), min_font_size)

    font, line_fit, bw, bh = fit_single_line_to_box(
        text_line=line,
        font_path=font_path,
        font_size=base_size,
        min_font_size=min_font_size,
        draw=draw,
        max_w=max_w,
        max_h=max_h,
        stroke_width=stroke_width
    )

    x, y = compute_anchor_xy(anchor, W, H, bw, bh, margin_x, margin_y)

    if readability_style in ("box", "both"):
        box = Image.new("RGBA", (bw, bh), background_box_fill)
        img.alpha_composite(box, dest=(x, y))

    draw.text(
        (x, y),
        line_fit,
        font=font,
        fill=text_color,
        stroke_width=stroke_width if readability_style in ("stroke", "both") else 0,
        stroke_fill=stroke_fill
    )

    return img


# =========================
# ОСНОВНОЙ ЦИКЛ
# =========================

def process_one_image(
    img_path: Path,
    cfg: dict,
    mode: str,
    block_lines: Optional[List[str]],
    dry_run: bool,
    indexing_kwargs: Optional[dict] = None
) -> Tuple[bool, Optional[Path]]:
    """
    Обработка одного изображения.
    - mode="full_text": block_lines — весь текст по строкам.
    - mode="line_block": block_lines — блок из N строк для этой картинки.
    - mode="single_line": block_lines = [одна строка].
    Возвращает (ok, out_path).
    """
    try:
        img = Image.open(img_path)
        if cfg.get("respect_exif_orientation", True):
            img = ImageOps.exif_transpose(img)

        if dry_run:
            preview = "\\n".join(block_lines or [])
            logging.info("[DRY RUN] %s → режим=%s, строк(в блоке)=%d; пример: %r",
                         img_path.name, mode, len(block_lines or []), preview[:80])
            return True, None

        if mode == "single_line":
            img = render_single_line_on_image(img, block_lines[0] if block_lines else "", cfg)
        else:
            img = render_text_block_on_image(img, block_lines or [""], cfg)

        save_format, save_ext = normalize_format_and_ext(img_path, cfg.get("save_format", ""))
        kw = indexing_kwargs or {}
        out_path = choose_output_path(
            src_img=img_path,
            output_dir=cfg.get("output_dir", ""),
            naming=cfg.get("output_naming", "suffix"),
            suffix=cfg.get("output_suffix", "_with_text"),
            save_ext=save_ext,
            **kw,
        )

        if out_path is None:
            logging.info("Пропуск сохранения (skip_if_exists): %s", img_path.name)
            return True, None

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
        return True, out_path

    except Exception as e:
        logging.exception("Ошибка при обработке %s: %s", img_path, e)
        return False, None


def try_delete_original(original_path: Path, out_path: Optional[Path], cfg: dict):
    """Удаляет исходную картинку, если это разрешено и безопасно."""
    if not bool(cfg.get("delete_original_after_success", False)):
        return
    if bool(cfg.get("dry_run", False)):
        return
    if out_path is None:
        return
    # Если сохраняли поверх исходника — удалять нечего (пути совпадают)
    try:
        if original_path.resolve() == out_path.resolve():
            return
    except Exception:
        if str(original_path) == str(out_path):
            return
    try:
        if original_path.exists():
            original_path.unlink()
            logging.info("Исходник удалён: %s", original_path)
    except Exception as e:
        logging.warning("Не удалось удалить исходник %s: %s", original_path, e)


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
    text_encoding = cfg.get("text_encoding", "utf-8") if cfg.get("text_encoding") else "utf-8"
    dry_run = bool(cfg.get("dry_run", False))

    match_mode = str(cfg.get("image_match_mode", "prefix")).lower()
    if match_mode not in ("exact", "prefix"):
        logging.warning("Неизвестный image_match_mode: %s — используем 'prefix'", match_mode)
        match_mode = "prefix"

    per_image_text_mode = str(cfg.get("per_image_text_mode", "full_text")).lower()
    if per_image_text_mode not in ("full_text", "line_by_line_cycle"):
        logging.warning("Неизвестный per_image_text_mode: %s — используем 'full_text'", per_image_text_mode)
        per_image_text_mode = "full_text"

    target_images = str(cfg.get("target_images", "all")).lower()
    if target_images not in ("all", "first"):
        logging.warning("Неизвестный target_images: %s — используем 'all'", target_images)
        target_images = "all"

    include_empty_lines = bool(cfg.get("include_empty_lines", False))
    lines_per_image = int(cfg.get("lines_per_image", 1))
    if lines_per_image < 1:
        logging.warning("lines_per_image<1 → принудительно 1")
        lines_per_image = 1

    remove_markers: List[str] = cfg.get("remove_markers", []) or []
    drop_lines_with_markers = bool(cfg.get("drop_lines_with_markers", False))

    # Индексация выходных файлов при цикле
    cycle_indexing = bool(cfg.get("cycle_output_indexing", False))
    cycle_index_start = int(cfg.get("cycle_index_start", 1))
    cycle_index_pad = int(cfg.get("cycle_index_pad", 0))
    cycle_tpl = str(cfg.get("cycle_index_name_template", "{stem}_{i}{suffix}{ext}"))

    total_txt = len(text_files)
    total_images = 0
    processed = 0
    skipped = 0
    no_images = 0

    for txt in text_files:
        # читаем и фильтруем сырой текст по маркерам
        try:
            raw_text = txt.read_text(encoding=text_encoding)
        except Exception as e:
            logging.error("Не удалось прочитать текст %s: %s", txt, e)
            skipped += 1
            continue

        filtered_text = filter_text_by_markers_raw(raw_text, remove_markers, drop_lines_with_markers)

        images = find_images_for_text(txt, image_exts, match_mode=match_mode)
        if not images:
            no_images += 1
            logging.info("Нет подходящих картинок для %s — пропуск.", txt.name)
            continue

        # Применяем режим "first", если выбран
        if target_images == "first":
            images = images[:1]

        total_images += len(images)

        if per_image_text_mode == "full_text":
            # Каждая выбранная картинка получает весь (уже отфильтрованный) текст
            lines_full = filtered_text.splitlines()
            if not include_empty_lines:
                lines_full = [ln for ln in lines_full if ln.strip() != ""]
            for img_path in images:
                ok, out_path = process_one_image(
                    img_path=img_path,
                    cfg=cfg,
                    mode="full_text",
                    block_lines=lines_full,
                    dry_run=dry_run,
                    indexing_kwargs=None  # индексация не нужна
                )
                if ok:
                    processed += 1
                    try_delete_original(img_path, out_path, cfg)
                else:
                    skipped += 1

        else:
            # line_by_line_cycle
            raw_lines = filtered_text.splitlines()
            lines = filter_lines_by_markers(raw_lines, remove_markers, drop_lines_with_markers)
            if not include_empty_lines:
                lines = [ln for ln in lines if ln.strip() != ""]
            if not lines:
                logging.info("TXT %s содержит 0 строк (после фильтра). Картинки будут пропущены.", txt.name)
                continue

            n_images = len(images)

            # Группируем строки пакетами по lines_per_image
            blocks: List[List[str]] = []
            curr: List[str] = []
            for ln in lines:
                curr.append(ln)
                if len(curr) == lines_per_image:
                    blocks.append(curr)
                    curr = []
            if curr:
                blocks.append(curr)

            # Счётчик использований и последний сохранённый путь для каждой картинки
            use_count: Dict[Path, int] = {p: 0 for p in images}
            last_out: Dict[Path, Optional[Path]] = {p: None for p in images}

            # Раздаём блоки по картинкам циклично
            for i, block in enumerate(blocks):
                img_path = images[i % n_images]
                use_count[img_path] += 1
                index_for_this = use_count[img_path] - 1 + cycle_index_start  # 1,2,3,...

                mode = "single_line" if len(block) == 1 else "line_block"

                indexing_kwargs = {}
                if cycle_indexing:
                    indexing_kwargs = dict(
                        index=index_for_this,
                        cycle_indexing=True,
                        cycle_index_start=cycle_index_start,
                        cycle_index_pad=cycle_index_pad,
                        cycle_tpl=cycle_tpl,
                    )

                ok, out_path = process_one_image(
                    img_path=img_path,
                    cfg=cfg,
                    mode=mode,
                    block_lines=block,
                    dry_run=dry_run,
                    indexing_kwargs=indexing_kwargs
                )
                if ok:
                    processed += 1
                    last_out[img_path] = out_path
                else:
                    skipped += 1

            # ПОСЛЕ цикла — удаляем исходники один раз для каждой картинки
            for p in images:
                try_delete_original(p, last_out[p], cfg)

    logging.info(
        "Готово. TXT: %d; найдено картинок: %d; успешно обработано: %d; без картинок: %d; ошибок: %d",
        total_txt, total_images, processed, no_images, skipped
    )


if __name__ == "__main__":
    main()
