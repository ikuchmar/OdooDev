# -*- coding: utf-8 -*-
"""
TXT → ищем картинки рядом → накладываем текст.

УПРОЩЁННЫЙ MULTI-SOURCES:
- Единственный параметр в config.toml:
    multi_sources_patterns = ["{base}_en.txt", "{base}_tr.txt", "{base}_ua.txt"]
- Если список пуст → старое поведение (один TXT).
- Если НЕ пуст:
    * Собираем файлы по порядку, общая "base" берётся из имени TXT.
    * Для индекса i берём i-ю строку из каждого найденного файла → формируем ОДИН БЛОК (несколько строк).
    * Идём до МАКСИМАЛЬНОЙ длины; отсутствующие строки пропускаем.
    * В этом режиме lines_per_image игнорируется (блок уже готов).
    * per_image_text_mode:
        - "line_by_line_cycle" → каждый блок = одна картинка (циклично по подходящим изображениям).
        - "full_text" → все блоки объединяются в один многострочный текст и кладутся на выбранную(ые) картинку(и).
    * Картинки ищем по ПЕРВОМУ реально найденному источнику из списка паттернов (учитывая image_match_mode).

Прочее:
- image_match_mode: exact/prefix
- target_images: all/first
- фильтрация маркеров remove_markers / drop_lines_with_markers
- индексация выходов при циклах
- безопасное удаление исходника — один раз после обработки всех блоков для этой картинки
- Python 3.11+ (tomllib), Pillow
"""

import sys
import logging
from typing import List, Tuple, Optional, Iterable, Dict, Any
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except Exception:
    print("Нужен Python 3.11+ (для tomllib).", file=sys.stderr)
    raise

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor


# =========================
# Конфиг/логирование
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


# =========================
# Сканирование TXT
# =========================

def collect_texts(input_dirs: List[str], input_files: List[str], recursive: bool) -> List[Path]:
    result: List[Path] = []
    for d in input_dirs or []:
        p = Path(d)
        if not p.exists():
            logging.warning("Папка не найдена: %s", p)
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


# =========================
# Цвет/каталоги
# =========================

def parse_color(value: str) -> Tuple[int, int, int, int]:
    v = value.strip()
    if v.startswith("#") and len(v) == 9:  # #RRGGBBAA
        r = int(v[1:3], 16); g = int(v[3:5], 16); b = int(v[5:7], 16); a = int(v[7:9], 16)
        return (r, g, b, a)
    rgb = ImageColor.getrgb(v)
    return (rgb[0], rgb[1], rgb[2], 255)


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


# =========================
# Позиционирование/рисование
# =========================

def compute_anchor_xy(anchor: str, W: int, H: int, bw: int, bh: int, mx: int, my: int) -> Tuple[int, int]:
    x = (W - bw) // 2; y = (H - bh) // 2
    a = anchor.lower()
    if "top" in a: y = my
    elif "bottom" in a: y = H - bh - my
    if a.endswith("left"): x = mx
    elif a.endswith("right"): x = W - bw - mx
    elif a.endswith("center"): x = (W - bw) // 2
    return x, y


def wrap_text_to_width(text: str, font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw, max_w: int) -> List[str]:
    lines: List[str] = []
    for raw in text.splitlines():
        if raw.strip() == "" and raw != "":
            lines.append("")
            continue
        words = raw.split(" ")
        if not words:
            lines.append("")
            continue
        cur = ""
        for w in words:
            cand = (cur + " " + w).strip() if cur else w
            width = draw.textbbox((0, 0), cand, font=font, stroke_width=0)[2]
            width -= draw.textbbox((0, 0), cand, font=font, stroke_width=0)[0]
            if width <= max_w or not cur:
                cur = cand
            else:
                lines.append(cur); cur = w
        if cur != "":
            lines.append(cur)
    return lines


def text_block_bbox(lines: List[str], font: ImageFont.FreeTypeFont, draw: ImageDraw.ImageDraw,
                    line_spacing: float, stroke_width: int) -> Tuple[int, int]:
    max_w, total_h, prev_h = 0, 0, 0
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line if line else " ", font=font, stroke_width=stroke_width)
        w = bbox[2]-bbox[0]; h = bbox[3]-bbox[1]
        max_w = max(max_w, w)
        total_h += h if i == 0 else int(prev_h * line_spacing)
        prev_h = h
    return max_w, total_h


def draw_multiline_text(img: Image.Image, xy: Tuple[int,int], lines: List[str],
                        font: ImageFont.FreeTypeFont, color: Tuple[int,int,int,int], align: str,
                        line_spacing: float, readability_style: str, stroke_width: int,
                        stroke_fill: Tuple[int,int,int,int], background_box_fill: Tuple[int,int,int,int]):
    draw = ImageDraw.Draw(img, "RGBA")
    bw, bh = text_block_bbox(lines, font, draw, line_spacing, stroke_width)
    x, y = xy
    if readability_style in ("box", "both"):
        box = Image.new("RGBA", (bw, bh), background_box_fill)
        img.alpha_composite(box, dest=(x, y))

    prev_h = 0; ly = y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0,0), line if line else " ", font=font, stroke_width=stroke_width)
        lw = bbox[2]-bbox[0]; lh = bbox[3]-bbox[1]
        ly = y if i == 0 else (ly + int(prev_h * line_spacing))
        prev_h = lh
        if align == "left": lx = x
        elif align == "right": lx = x + (bw - lw)
        else: lx = x + (bw - lw)//2
        draw.text((lx, ly), line, font=font, fill=color,
                  stroke_width=stroke_width if readability_style in ("stroke","both") else 0,
                  stroke_fill=stroke_fill)


# =========================
# Сохранение/выбор путей
# =========================

def normalize_format_and_ext(src: Path, save_format_cfg: str) -> Tuple[str, str]:
    if save_format_cfg:
        fmt = save_format_cfg.upper()
        if fmt in ("JPEG","PNG","WEBP"):
            return (fmt, ".jpg" if fmt=="JPEG" else ".png" if fmt=="PNG" else ".webp")
        else:
            logging.warning("Неподдерживаемый save_format '%s'. Используем исходник.", fmt)
    ext = src.suffix.lower()
    if ext in (".jpg",".jpeg"): return "JPEG", ".jpg"
    if ext == ".png": return "PNG", ".png"
    if ext == ".webp": return "WEBP", ".webp"
    logging.warning("Неожиданное расширение '%s' у %s. Сохраняем как PNG.", ext, src.name)
    return "PNG", ".png"


def choose_output_path(src_img: Path, output_dir: str, naming: str, suffix: str, save_ext: str,
                       *, index: Optional[int]=None, cycle_indexing: bool=False,
                       cycle_index_start: int=1, cycle_index_pad: int=0,
                       cycle_tpl: str="{stem}_{i}{suffix}{ext}") -> Optional[Path]:
    if naming not in ("suffix","overwrite","skip_if_exists"):
        logging.warning("Неизвестный output_naming: %s → 'suffix'", naming)
        naming = "suffix"
    stem = src_img.stem; ext = save_ext

    def with_suffix(base_stem: str) -> str:
        return (base_stem + suffix) if naming == "suffix" else base_stem

    if cycle_indexing and index is not None:
        i_val = max(index, cycle_index_start)
        i_str = str(i_val).zfill(max(0, cycle_index_pad))
        out_stem = cycle_tpl.format(stem=stem, i=i_str, suffix=(suffix if naming=="suffix" else ""), ext="")
        filename = out_stem + ext
        out_path = Path(output_dir, filename) if output_dir else src_img.with_name(filename)
        ensure_dir(out_path.parent)
        if naming == "skip_if_exists" and out_path.exists():
            return None
        return out_path

    if output_dir:
        base = Path(output_dir) / src_img.name
        if naming == "suffix":
            if suffix == "":
                logging.warning("suffix='' при naming='suffix' → фактический overwrite: %s", src_img.name)
            base = base.with_stem(with_suffix(base.stem))
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
            logging.warning("suffix='' при naming='suffix' → фактический overwrite: %s", src_img.name)
        return src_img.with_stem(with_suffix(src_img.stem)).with_suffix(ext)


# =========================
# Поиск картинок
# =========================

def find_images_for_text(txt_path: Path, image_exts: Iterable[str], match_mode: str) -> List[Path]:
    folder = txt_path.parent
    if not folder.exists():
        return []
    base = txt_path.stem.lower()
    exts = set(e.lower() for e in image_exts)
    res: List[Path] = []
    for f in folder.iterdir():
        if not f.is_file(): continue
        if f.suffix.lower() not in exts: continue
        name = f.stem.lower()
        if match_mode == "exact":
            if name == base: res.append(f)
        else:
            if name.startswith(base): res.append(f)
    return sorted(res)


# =========================
# Фильтрация текста
# =========================

def filter_text_by_markers_raw(text: str, markers: List[str], drop_lines: bool) -> str:
    if not markers: return text
    if drop_lines:
        kept = [ln for ln in text.splitlines() if not any(m in ln for m in markers)]
        return "\n".join(kept)
    cleaned = text
    for m in markers:
        if m: cleaned = cleaned.replace(m, "")
    return cleaned


def filter_lines_by_markers(lines: List[str], markers: List[str], drop_lines: bool) -> List[str]:
    if not markers: return lines
    if drop_lines:
        return [ln for ln in lines if not any(m in ln for m in markers)]
    out = []
    for ln in lines:
        for m in markers:
            if m: ln = ln.replace(m, "")
        out.append(ln)
    return out


# =========================
# Рендеринг текста
# =========================

def fit_single_line_to_box(text_line: str, font_path: str, font_size: int, min_font_size: int,
                           draw: ImageDraw.ImageDraw, max_w: int, max_h: int,
                           stroke_width: int) -> Tuple[ImageFont.FreeTypeFont, str, int, int]:
    size = font_size
    font = ImageFont.truetype(font_path, size)

    def bbox(line: str) -> Tuple[int,int]:
        bb = draw.textbbox((0,0), line if line else " ", font=font, stroke_width=stroke_width)
        return bb[2]-bb[0], bb[3]-bb[1]

    bw, bh = bbox(text_line)
    while (bw > max_w or bh > max_h) and size > min_font_size:
        size -= 1; font = ImageFont.truetype(font_path, size); bw, bh = bbox(text_line)

    if bw > max_w:
        ell = "…"; base = text_line
        while base and (draw.textbbox((0,0), base+ell, font=font, stroke_width=stroke_width)[2] >
                        max_w):
            base = base[:-1]
        text_line = (base+ell) if base else ell
        bw, bh = bbox(text_line)
    return font, text_line, bw, bh


def render_text_block_on_image(img: Image.Image, text_lines: List[str], cfg: dict) -> Image.Image:
    if img.mode != "RGBA": img = img.convert("RGBA")
    W,H = img.size
    max_w = int(W*float(cfg.get("max_width_pct",0.9)))
    max_h = int(H*float(cfg.get("max_height_pct",0.5)))
    mx = int(cfg.get("margin_x",32)); my = int(cfg.get("margin_y",32))
    anchor = str(cfg.get("anchor","bottom_center")).lower()
    align = str(cfg.get("align","center")).lower()
    line_spacing = float(cfg.get("line_spacing",1.2))

    readability_style = str(cfg.get("readability_style","both")).lower()
    stroke_width = int(cfg.get("stroke_width",2))
    stroke_fill = parse_color(cfg.get("stroke_fill","#000000"))
    background_box_fill = parse_color(cfg.get("background_box_fill","#00000080"))
    color = parse_color(cfg.get("color","#FFFFFF"))

    font_path = cfg.get("font_path");
    if not font_path or not Path(font_path).is_file():
        raise FileNotFoundError(f"font_path не найден: {font_path}")
    min_font = int(cfg.get("min_font_size",14))
    font_size_cfg = cfg.get("font_size","auto")

    draw = ImageDraw.Draw(img, "RGBA")
    fs = int(font_size_cfg) if isinstance(font_size_cfg,int) else max(int(H*0.07), min_font)
    font = ImageFont.truetype(font_path, fs)

    wrapped = wrap_text_to_width("\n".join(text_lines), font, draw, max_w)
    bw,bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)
    while bh > max_h and fs > min_font:
        fs -= 1; font = ImageFont.truetype(font_path, fs)
        wrapped = wrap_text_to_width("\n".join(text_lines), font, draw, max_w)
        bw,bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

    if bh > max_h and fs == min_font:
        logging.warning("Блок не помещается даже при min_font_size=%d — будет усечён.", min_font)
        while wrapped and text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)[1] > max_h:
            wrapped = wrapped[:-1]
        if wrapped: wrapped[-1] = (wrapped[-1] + "…").rstrip()
        bw,bh = text_block_bbox(wrapped, font, draw, line_spacing, stroke_width)

    bw = min(bw, max_w); bh = min(bh, max_h)
    x,y = compute_anchor_xy(anchor, W,H, bw,bh, mx,my)
    draw_multiline_text(img,(x,y), wrapped, font, color, align, line_spacing,
                        readability_style, stroke_width, stroke_fill, background_box_fill)
    return img


def render_single_line_on_image(img: Image.Image, line: str, cfg: dict) -> Image.Image:
    if img.mode != "RGBA": img = img.convert("RGBA")
    W,H = img.size
    max_w = int(W*float(cfg.get("max_width_pct",0.9)))
    max_h = int(H*float(cfg.get("max_height_pct",0.5)))
    mx = int(cfg.get("margin_x",32)); my = int(cfg.get("margin_y",32))
    anchor = str(cfg.get("anchor","bottom_center")).lower()

    readability_style = str(cfg.get("readability_style","both")).lower()
    stroke_width = int(cfg.get("stroke_width",2))
    stroke_fill = parse_color(cfg.get("stroke_fill","#000000"))
    background_box_fill = parse_color(cfg.get("background_box_fill","#00000080"))
    color = parse_color(cfg.get("color","#FFFFFF"))

    font_path = cfg.get("font_path")
    if not font_path or not Path(font_path).is_file():
        raise FileNotFoundError(f"font_path не найден: {font_path}")
    min_font = int(cfg.get("min_font_size",14))
    font_size_cfg = cfg.get("font_size","auto")

    draw = ImageDraw.Draw(img, "RGBA")
    base_size = int(font_size_cfg) if isinstance(font_size_cfg,int) else max(int(H*0.07), min_font)
    font, line_fit, bw, bh = fit_single_line_to_box(line, font_path, base_size, min_font,
                                                    draw, max_w, max_h, stroke_width)
    x,y = compute_anchor_xy(anchor, W,H, bw,bh, mx,my)
    if readability_style in ("box","both"):
        box = Image.new("RGBA", (bw,bh), background_box_fill)
        img.alpha_composite(box, dest=(x,y))
    ImageDraw.Draw(img, "RGBA").text((x,y), line_fit, font=font, fill=color,
                                     stroke_width=stroke_width if readability_style in ("stroke","both") else 0,
                                     stroke_fill=stroke_fill)
    return img


# =========================
# Сохранение/удаление
# =========================

def process_one_image(img_path: Path, cfg: dict, mode: str,
                      block_lines: Optional[List[str]], dry_run: bool,
                      indexing_kwargs: Optional[dict]=None) -> Tuple[bool, Optional[Path]]:
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

        save_format, save_ext = normalize_format_and_ext(img_path, cfg.get("save_format",""))
        kw = indexing_kwargs or {}
        out_path = choose_output_path(
            src_img=img_path,
            output_dir=cfg.get("output_dir",""),
            naming=cfg.get("output_naming","suffix"),
            suffix=cfg.get("output_suffix","_with_text"),
            save_ext=save_ext,
            **kw,
        )
        if out_path is None:
            logging.info("Пропуск сохранения (skip_if_exists): %s", img_path.name)
            return True, None

        params = {}
        img_to_save = img
        if save_format == "JPEG":
            params["quality"] = int(cfg.get("jpeg_quality",90))
            params["subsampling"] = "4:2:0"
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255,255,255))
                bg.paste(img, mask=img.split()[3])
                img_to_save = bg
            else:
                img_to_save = img.convert("RGB")
        elif save_format == "WEBP":
            params["quality"] = int(cfg.get("webp_quality",90))

        ensure_dir(out_path.parent)
        img_to_save.save(out_path, format=save_format, **params)
        logging.info("Сохранено: %s", out_path)
        return True, out_path

    except Exception as e:
        logging.exception("Ошибка при обработке %s: %s", img_path, e)
        return False, None


def try_delete_original(original_path: Path, out_path: Optional[Path], cfg: dict):
    if not bool(cfg.get("delete_original_after_success", False)): return
    if bool(cfg.get("dry_run", False)): return
    if out_path is None: return
    try:
        if original_path.resolve() == out_path.resolve(): return
    except Exception:
        if str(original_path) == str(out_path): return
    try:
        if original_path.exists():
            original_path.unlink()
            logging.info("Исходник удалён: %s", original_path)
    except Exception as e:
        logging.warning("Не удалось удалить исходник %s: %s", original_path, e)


# =========================
# Multi-sources (один параметр)
# =========================

def _extract_suffix(pat: str) -> str:
    """Фиксированная часть после {base} перед .txt. Пример: '_en'."""
    if "{base}" not in pat or not pat.endswith(".txt"): return ""
    after = pat.split("{base}", 1)[1]
    return after[:-4]  # без '.txt'


def _detect_base_by_patterns(txt_name: str, patterns: List[str]) -> Optional[str]:
    """Пытаемся извлечь base из имени TXT по первому подходящему паттерну (без звёздочек)."""
    if not txt_name.lower().endswith(".txt"): return None
    name = txt_name[:-4]
    for pat in patterns:
        if "{base}" not in pat or not pat.endswith(".txt"): continue
        suffix = _extract_suffix(pat)
        if "*" in suffix:
            # Упрощение: звёздочки в этом варианте не поддерживаем — держим паттерны явными.
            continue
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[:-len(suffix)]
    return None


def _read_filtered_lines(p: Path, encoding: str, markers: List[str], drop_lines: bool, include_empty: bool) -> List[str]:
    raw = p.read_text(encoding=encoding)
    raw = filter_text_by_markers_raw(raw, markers, drop_lines)
    lines = raw.splitlines()
    if not include_empty:
        lines = [ln for ln in lines if ln.strip() != ""]
    return lines


def build_blocks_from_patterns(folder: Path, base: str, patterns: List[str], cfg: dict) -> Tuple[List[List[str]], Optional[Path]]:
    """
    Возвращает (blocks, primary_txt_path).
    blocks: список блоков; каждый блок — список строк (например EN+TR+UA).
    primary_txt_path: первый реально существующий файл из списка — нужен, чтобы искать картинки.
    """
    text_encoding = cfg.get("text_encoding", "utf-8") or "utf-8"
    remove_markers: List[str] = cfg.get("remove_markers", []) or []
    drop_lines_with_markers = bool(cfg.get("drop_lines_with_markers", False))
    include_empty_lines = bool(cfg.get("include_empty_lines", False))

    sources: List[Dict[str, Any]] = []
    primary: Optional[Path] = None

    # Читаем источники в порядке паттернов
    for pat in patterns:
        if "{base}" not in pat or not pat.endswith(".txt"):
            continue
        suffix = _extract_suffix(pat)
        path = folder / (base + suffix + ".txt")
        lines: List[str] = []
        if path.exists():
            try:
                lines = _read_filtered_lines(path, text_encoding, remove_markers, drop_lines_with_markers, include_empty_lines)
                if primary is None:
                    primary = path
            except Exception as e:
                logging.warning("Не удалось прочитать %s: %s", path, e)
        sources.append({"suffix": suffix, "path": path if path.exists() else None, "lines": lines})

    if not any(s["lines"] for s in sources):
        return [], primary

    # Формируем блоки по максимальной длине
    max_len = max(len(s["lines"]) for s in sources)
    blocks: List[List[str]] = []
    for i in range(max_len):
        block: List[str] = []
        for s in sources:
            if i < len(s["lines"]):
                block.append(s["lines"][i])
            else:
                # пропускаем отсутствующие
                pass
        if block:
            blocks.append(block)

    return blocks, primary


# =========================
# Верхний уровень
# =========================

def main():
    cfg_path = Path(__file__).with_name("config.toml")
    if not cfg_path.exists():
        print("Не найден config.toml рядом со скриптом.", file=sys.stderr)
        sys.exit(2)

    cfg = load_config(cfg_path)
    setup_logging(cfg.get("logging_level","INFO"), bool(cfg.get("log_to_file",False)), str(cfg.get("log_file","overlay.log")))
    logging.info("Старт. Конфиг: %s", cfg_path)

    recursive = bool(cfg.get("recursive", True))
    text_files = collect_texts(cfg.get("input_dirs", []), cfg.get("input_files", []), recursive)
    if not text_files:
        logging.warning("TXT-файлы не найдены.")
        return

    image_exts = [e.lower() for e in cfg.get("image_extensions", [".jpg",".jpeg",".png",".webp"])]
    match_mode = str(cfg.get("image_match_mode", "prefix")).lower()
    if match_mode not in ("exact","prefix"):
        logging.warning("Неизвестный image_match_mode: %s → 'prefix'", match_mode)
        match_mode = "prefix"

    per_image_text_mode = str(cfg.get("per_image_text_mode","full_text")).lower()
    if per_image_text_mode not in ("full_text","line_by_line_cycle"):
        logging.warning("Неизвестный per_image_text_mode: %s → 'full_text'", per_image_text_mode)
        per_image_text_mode = "full_text"

    target_images = str(cfg.get("target_images","all")).lower()
    if target_images not in ("all","first"):
        logging.warning("Неизвестный target_images: %s → 'all'", target_images)
        target_images = "all"

    include_empty_lines = bool(cfg.get("include_empty_lines", False))
    lines_per_image = int(cfg.get("lines_per_image", 1))
    if lines_per_image < 1:
        logging.warning("lines_per_image<1 → 1")
        lines_per_image = 1

    cycle_indexing = bool(cfg.get("cycle_output_indexing", False))
    cycle_index_start = int(cfg.get("cycle_index_start", 1))
    cycle_index_pad = int(cfg.get("cycle_index_pad", 0))
    cycle_tpl = str(cfg.get("cycle_index_name_template", "{stem}_{i}{suffix}{ext}"))

    patterns: List[str] = cfg.get("multi_sources_patterns", []) or []
    ms_enabled = len(patterns) > 0

    total_txt = len(text_files)
    total_images = 0
    processed = 0
    skipped = 0
    no_images = 0

    processed_bases: set[Tuple[Path, str]] = set()

    # Односоставный режим: чтение/фильтрация
    text_encoding = cfg.get("text_encoding","utf-8") or "utf-8"
    remove_markers: List[str] = cfg.get("remove_markers", []) or []
    drop_lines_with_markers = bool(cfg.get("drop_lines_with_markers", False))

    for txt in text_files:
        folder = txt.parent

        if ms_enabled:
            base = _detect_base_by_patterns(txt.name, patterns)
            if base:
                key = (folder, base)
                if key in processed_bases:
                    continue
                processed_bases.add(key)

                blocks, primary_txt = build_blocks_from_patterns(folder, base, patterns, cfg)
                if not blocks:
                    logging.info("Нет данных (multi-sources) для base='%s' в %s", base, folder)
                    continue

                anchor_txt = primary_txt if primary_txt else (folder / (base + _extract_suffix(patterns[0]) + ".txt"))
                images = find_images_for_text(anchor_txt, image_exts, match_mode=match_mode)
                if not images:
                    no_images += 1
                    logging.info("Нет подходящих картинок для %s — пропуск.", anchor_txt.name)
                    continue

                if target_images == "first":
                    images = images[:1]
                total_images += len(images)

                n_images = len(images)
                use_count: Dict[Path, int] = {p: 0 for p in images}
                last_out: Dict[Path, Optional[Path]] = {p: None for p in images}

                if per_image_text_mode == "full_text":
                    merged: List[str] = []
                    for b in blocks: merged.extend(b)
                    for img_path in images:
                        ok, out_path = process_one_image(img_path, cfg, "full_text", merged, bool(cfg.get("dry_run",False)), None)
                        if ok: processed += 1; last_out[img_path] = out_path
                        else: skipped += 1
                    for p in images:
                        try_delete_original(p, last_out[p], cfg)
                else:
                    # line_by_line_cycle: каждый блок → одна картинка (циклично)
                    for i, block in enumerate(blocks):
                        img_path = images[i % n_images]
                        use_count[img_path] += 1
                        idx_for = use_count[img_path] - 1 + cycle_index_start
                        mode = "single_line" if len(block) == 1 else "line_block"
                        idx_kwargs = {}
                        if cycle_indexing:
                            idx_kwargs = dict(index=idx_for, cycle_indexing=True,
                                              cycle_index_start=cycle_index_start,
                                              cycle_index_pad=cycle_index_pad,
                                              cycle_tpl=cycle_tpl)
                        ok, out_path = process_one_image(img_path, cfg, mode, block, bool(cfg.get("dry_run",False)), idx_kwargs)
                        if ok: processed += 1; last_out[img_path] = out_path
                        else: skipped += 1
                    for p in images:
                        try_delete_original(p, last_out[p], cfg)
                continue  # к следующему TXT

            # иначе — этот TXT не попал под паттерны → обработаем в одиночном режиме ниже

        # ---- ОДИНОЧНЫЙ РЕЖИМ (как раньше) ----
        try:
            raw_text = txt.read_text(encoding=text_encoding)
        except Exception as e:
            logging.error("Не удалось прочитать текст %s: %s", txt, e)
            skipped += 1
            continue

        filtered = filter_text_by_markers_raw(raw_text, remove_markers, drop_lines_with_markers)
        images = find_images_for_text(txt, image_exts, match_mode=match_mode)
        if not images:
            no_images += 1
            logging.info("Нет подходящих картинок для %s — пропуск.", txt.name)
            continue

        if target_images == "first":
            images = images[:1]
        total_images += len(images)

        if per_image_text_mode == "full_text":
            lines_full = filtered.splitlines()
            if not include_empty_lines:
                lines_full = [ln for ln in lines_full if ln.strip() != ""]
            for img_path in images:
                ok, out_path = process_one_image(img_path, cfg, "full_text", lines_full, bool(cfg.get("dry_run",False)), None)
                if ok: processed += 1; try_delete_original(img_path, out_path, cfg)
                else: skipped += 1
        else:
            raw_lines = filtered.splitlines()
            lines = filter_lines_by_markers(raw_lines, remove_markers, drop_lines_with_markers)
            if not include_empty_lines:
                lines = [ln for ln in lines if ln.strip() != ""]
            if not lines:
                logging.info("TXT %s пуст после фильтра — пропуск.", txt.name)
                continue

            # Разбивка по lines_per_image (ТОЛЬКО для одиночного режима)
            blocks: List[List[str]] = []
            curr: List[str] = []
            for ln in lines:
                curr.append(ln)
                if len(curr) == lines_per_image:
                    blocks.append(curr); curr = []
            if curr: blocks.append(curr)

            n_images = len(images)
            use_count: Dict[Path, int] = {p: 0 for p in images}
            last_out: Dict[Path, Optional[Path]] = {p: None for p in images}

            for i, block in enumerate(blocks):
                img_path = images[i % n_images]
                use_count[img_path] += 1
                idx_for = use_count[img_path] - 1 + cycle_index_start
                mode = "single_line" if len(block) == 1 else "line_block"
                idx_kwargs = {}
                if cycle_indexing:
                    idx_kwargs = dict(index=idx_for, cycle_indexing=True,
                                      cycle_index_start=cycle_index_start,
                                      cycle_index_pad=cycle_index_pad,
                                      cycle_tpl=cycle_tpl)
                ok, out_path = process_one_image(img_path, cfg, mode, block, bool(cfg.get("dry_run",False)), idx_kwargs)
                if ok: processed += 1; last_out[img_path] = out_path
                else: skipped += 1
            for p in images:
                try_delete_original(p, last_out[p], cfg)

    logging.info("Готово. TXT: %d; найдено картинок: %d; успешно: %d; без картинок: %d; ошибок: %d",
                 total_txt, total_images, processed, no_images, skipped)


if __name__ == "__main__":
    main()
