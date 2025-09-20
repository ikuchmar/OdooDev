#!/usr/bin/env python3
# 03_render / render.py
# Подпрограмма "render", совместимая по настройкам с прежней draw_graph.py:
# - Читает TOML-граф и конфиг config_render.toml (структура ключей как в run.toml старой версии)
# - Использует те же defaults (block.*, font.*, theme.*, style.*) и layout-настройки (direction, gaps) для фолбэка
# - Рисует: прямоугольные/скруглённые блоки, шапку + разделители свойств, подписи по центру (по умолчанию),
#           стрелки (straight|orthogonal|auto), коннекторы (auto|left|right|top|bottom), подписи рёбер курсивом (опция)
# - НЕ выполняет миграцию/запись auto_* обратно в граф (это обязанность других этапов)
#
# Если в блоках присутствуют pos или auto_pos — использует их.
# Иначе выполняет упрощённую layered-раскладку (как в draw_graph.py) на основе [layout] в конфиге.

import sys, math, fnmatch
import tomllib
from pathlib import Path

# ----------------- utils -----------------

def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def discover_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns):
    files = []
    for d in input_dirs:
        base = Path(d)
        if not base.exists():
            continue
        it = base.rglob("*") if recursive else base.glob("*")
        for p in it:
            if not p.is_file():
                continue
            if include_exts:
                if p.suffix.lstrip(".").lower() not in [e.lower().lstrip(".") for e in include_exts]:
                    continue
            if input_suffix and not str(p).endswith(input_suffix):
                continue
            rel = str(p).replace("\\", "/")
            if any(fnmatch.fnmatch(rel, pat) for pat in (exclude_patterns or [])):
                continue
            files.append(p)
    return files

def svg_escape(s: str) -> str:
    return (str(s) if s is not None else "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def _get_dotted(D: dict, dotted: str, default=None):
    """Safely extract nested TOML values written with dotted keys inside a table.
    Example: in [defaults] with "block.width = 0.10", D == {"block":{"width":0.10}}.
    _get_dotted(D, "block.width") -> 0.10
    """
    cur = D
    for k in str(dotted).split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# ----------------- data model -----------------

class Defaults:
    def __init__(self, D: dict):
        self.canvas_size = tuple(D.get("canvas_size", [1200, 800]))
        # размеры/стили блока
        self.block_width = float(_get_dotted(D, "block.width", 0.10))
        self.block_header_height = float(_get_dotted(D, "block.header_height", 0.10))
        self.block_prop_height = float(_get_dotted(D, "block.prop_height", 0.06))
        self.block_shape = _get_dotted(D, "block.shape", "rounded")
        self.block_corner_radius = float(_get_dotted(D, "block.corner_radius", 10.0))
        self.block_stroke_width = float(_get_dotted(D, "block.stroke_width", 2.0))
        self.block_fill = _get_dotted(D, "block.fill_color", "none")
        self.block_stroke = _get_dotted(D, "block.stroke_color", "#000000")
        # шрифты
        self.font_family = _get_dotted(D, "font.family", "Arial")
        self.font_size_title = int(_get_dotted(D, "font.size_title", 14))
        self.font_size_prop  = int(_get_dotted(D, "font.size_prop", 12))
        self.font_bold_title = bool(_get_dotted(D, "font.bold_title", True))
        self.font_italic_arrow = bool(_get_dotted(D, "font.italic_arrow", True))
        # текст внутри блоков
        self.text_align_title = _get_dotted(D, "block.text_align_title", "center")
        self.text_align_props = _get_dotted(D, "block.text_align_props", "center")
        self.text_valign_title = _get_dotted(D, "block.text_valign_title", "middle")
        self.text_valign_props = _get_dotted(D, "block.text_valign_props", "middle")
        self.text_padding_title_x = float(_get_dotted(D, "block.text_padding_title_x", 6))
        self.text_padding_title_y = float(_get_dotted(D, "block.text_padding_title_y", 6))
        self.text_padding_prop_x  = float(_get_dotted(D, "block.text_padding_prop_x", 6))
        self.text_padding_prop_y  = float(_get_dotted(D, "block.text_padding_prop_y", 6))
        # тема
        self.theme_background = _get_dotted(D, "theme.background", "#FFFFFF")
        self.theme_text = _get_dotted(D, "theme.text_color", "#000000")
        self.theme_arrow = _get_dotted(D, "theme.arrow_color", "#222222")
        # стрелки
        self.style_curve = _get_dotted(D, "style.curve", "auto")
        self.style_label_offset = float(_get_dotted(D, "style.label_offset", 0.5))
        self.style_connector_from = _get_dotted(D, "style.connector_from", "auto")
        self.style_connector_to   = _get_dotted(D, "style.connector_to", "auto")
        self.style_arrow_size = float(_get_dotted(D, "style.arrow_size", 1.0))
        self.style_arrow_thickness = float(_get_dotted(D, "style.arrow_thickness", 2.0))

class LayoutCfg:
    def __init__(self, L: dict):
        self.mode = L.get("mode", "layered")      # layered|off
        self.direction = L.get("direction", "LR") # LR|RL|TB|BT
        self.node_gap = float(L.get("node_gap", 0.03))
        self.layer_gap = float(L.get("layer_gap", 0.08))
        self.respect_fixed_blocks = bool(L.get("respect_fixed_blocks", True))

    def __init__(self, L: dict):
        self.mode = L.get("mode", "layered")      # layered|off
        self.direction = L.get("direction", "LR") # LR|RL|TB|BT
        self.node_gap = float(L.get("node_gap", 0.03))
        self.layer_gap = float(L.get("layer_gap", 0.08))
        self.respect_fixed_blocks = bool(L.get("respect_fixed_blocks", True))

class Block:
    def __init__(self, raw: dict, idx: int):
        self.id = str(raw.get("id") or f"b{idx}")
        self.title = str(raw.get("title") or self.id)
        # свойства могут быть в ключе properties или props
        props = raw.get("properties", raw.get("props", []))
        if isinstance(props, dict):
            self.properties = [f"{k}: {v}" for k, v in props.items()]
        elif isinstance(props, list):
            self.properties = [str(x) for x in props]
        else:
            self.properties = []

        # размеры (нормированные), могут быть ручные или auto_*
        self.width = raw.get("width", raw.get("auto_width"))
        self.header_height = raw.get("header_height", raw.get("auto_header_height"))
        self.prop_height = raw.get("prop_height", raw.get("auto_prop_height"))

        # позиция (нормированная)
        self.pos = _tup2(raw.get("pos"))
        self.auto_pos = _tup2(raw.get("auto_pos"))

        # стиль блока — ручной/auto
        self.shape = raw.get("shape", raw.get("auto_shape"))
        self.corner_radius = raw.get("corner_radius", raw.get("auto_corner_radius"))
        self.stroke_width = raw.get("stroke_width", raw.get("auto_stroke_width"))
        self.fill = raw.get("fill", raw.get("auto_fill"))
        self.stroke = raw.get("stroke", raw.get("auto_stroke"))

        # шрифты
        self.font_family = raw.get("font.family", raw.get("auto_font_family"))
        self.font_size_title = raw.get("font.size_title", raw.get("auto_font_size_title"))
        self.font_size_prop  = raw.get("font.size_prop",  raw.get("auto_font_size_prop"))
        self.font_bold_title = raw.get("font.bold_title", raw.get("auto_font_bold_title"))
        self.font_italic_arrow = raw.get("font.italic_arrow", raw.get("auto_font_italic_arrow"))

        # текст
        self.text_align_title = raw.get("text_align_title", raw.get("auto_text_align_title"))
        self.text_align_props = raw.get("text_align_props", raw.get("auto_text_align_props"))
        self.text_valign_title = raw.get("text_valign_title", raw.get("auto_text_valign_title"))
        self.text_valign_props = raw.get("text_valign_props", raw.get("auto_text_valign_props"))
        self.text_padding_title_x = raw.get("text_padding_title_x", raw.get("auto_text_padding_title_x"))
        self.text_padding_title_y = raw.get("text_padding_title_y", raw.get("auto_text_padding_title_y"))
        self.text_padding_prop_x  = raw.get("text_padding_prop_x", raw.get("auto_text_padding_prop_x"))
        self.text_padding_prop_y  = raw.get("text_padding_prop_y", raw.get("auto_text_padding_prop_y"))

        # вычислимые пиксели
        self.cx_px = self.cy_px = 0.0
        self.w_px = self.h_px = 0.0

        # связи
        self.outs = []
        outs = raw.get("outs", [])
        if isinstance(outs, list):
            if outs and isinstance(outs[0], dict):
                for o in outs:
                    to = o.get("to")
                    if not to: 
                        continue
                    self.outs.append({
                        "to": str(to),
                        "label": o.get("label"),
                        "style.curve": (o.get("style", {}) or {}).get("curve", o.get("style.curve")),
                        "style.label_offset": (o.get("style", {}) or {}).get("label_offset", o.get("style.label_offset")),
                        "style.connector_from": (o.get("style", {}) or {}).get("connector_from", o.get("style.connector_from")),
                        "style.connector_to": (o.get("style", {}) or {}).get("connector_to", o.get("style.connector_to")),
                    })
            else:
                for to in outs:
                    self.outs.append({"to": str(to), "label": None})

    # эффективные значения (с дефолтом)
    def eff_pos(self):
        return self.pos or self.auto_pos
    def eff_width(self, d: Defaults):
        return float(self.width if self.width is not None else d.block_width)
    def eff_header(self, d: Defaults):
        return float(self.header_height if self.header_height is not None else d.block_header_height)
    def eff_prop(self, d: Defaults):
        return float(self.prop_height if self.prop_height is not None else d.block_prop_height)
    def eff_shape(self, d: Defaults):
        return (self.shape or d.block_shape).lower()
    def eff_corner_radius(self, d: Defaults):
        return float(self.corner_radius if self.corner_radius is not None else d.block_corner_radius)
    def eff_stroke_width(self, d: Defaults):
        return float(self.stroke_width if self.stroke_width is not None else d.block_stroke_width)
    def eff_fill(self, d: Defaults):
        return str(self.fill if self.fill is not None else d.block_fill)
    def eff_stroke(self, d: Defaults):
        return str(self.stroke if self.stroke is not None else d.block_stroke)
    def eff_font_family(self, d: Defaults):
        return str(self.font_family if self.font_family is not None else d.font_family)
    def eff_font_size_title(self, d: Defaults):
        return int(self.font_size_title if self.font_size_title is not None else d.font_size_title)
    def eff_font_size_prop(self, d: Defaults):
        return int(self.font_size_prop if self.font_size_prop is not None else d.font_size_prop)
    def eff_font_bold_title(self, d: Defaults):
        return bool(self.font_bold_title if self.font_bold_title is not None else d.font_bold_title)
    def eff_font_italic_arrow(self, d: Defaults):
        return bool(self.font_italic_arrow if self.font_italic_arrow is not None else d.font_italic_arrow)
    def eff_text_align_title(self, d: Defaults):
        return str(self.text_align_title if self.text_align_title is not None else d.text_align_title)
    def eff_text_align_props(self, d: Defaults):
        return str(self.text_align_props if self.text_align_props is not None else d.text_align_props)
    def eff_text_valign_title(self, d: Defaults):
        return str(self.text_valign_title if self.text_valign_title is not None else d.text_valign_title)
    def eff_text_valign_props(self, d: Defaults):
        return str(self.text_valign_props if self.text_valign_props is not None else d.text_valign_props)
    def eff_text_pad_title_x(self, d: Defaults):
        return float(self.text_padding_title_x if self.text_padding_title_x is not None else d.text_padding_title_x)
    def eff_text_pad_title_y(self, d: Defaults):
        return float(self.text_padding_title_y if self.text_padding_title_y is not None else d.text_padding_title_y)
    def eff_text_pad_prop_x(self, d: Defaults):
        return float(self.text_padding_prop_x if self.text_padding_prop_x is not None else d.text_padding_prop_x)
    def eff_text_pad_prop_y(self, d: Defaults):
        return float(self.text_padding_prop_y if self.text_padding_prop_y is not None else d.text_padding_prop_y)

def _tup2(v):
    return (float(v[0]), float(v[1])) if isinstance(v, list) and len(v) == 2 else None

# ----------------- layout (fallback) -----------------

def layered_layout(blocks, arrows, layout: LayoutCfg):
    # Если у большинства есть pos — просто уходим (используем заданные)
    have_pos = sum(1 for b in blocks if b.eff_pos() is not None)
    if have_pos >= max(1, len(blocks) // 2):
        return  # считаем, что позиции заданы

    # Граф смежности
    ids = {b.id for b in blocks}
    incoming = {b.id: [] for b in blocks}
    outgoing = {b.id: [] for b in blocks}
    for b in blocks:
        for o in b.outs:
            to = o.get("to")
            if to in ids:
                outgoing[b.id].append(to)
                incoming[to].append(b.id)

    # Источники
    srcs = [k for k, v in incoming.items() if not v] or ([blocks[0].id] if blocks else [])
    INF = 10**9
    layer = {bid: INF for bid in ids}
    for s in srcs: layer[s] = 0
    fr = srcs[:]
    while fr:
        nf = []
        for u in fr:
            for v in outgoing.get(u, []):
                if layer[v] > layer[u] + 1:
                    layer[v] = layer[u] + 1
                    nf.append(v)
        fr = nf
    max_layer = max([0] + [v for v in layer.values() if v < INF])
    for bid, lv in list(layer.items()):
        if lv == INF:
            max_layer += 1
            layer[bid] = max_layer

    # Группы по слоям
    by_layer = {}
    for bid, lv in layer.items():
        by_layer.setdefault(int(lv), []).append(bid)
    order = sorted(by_layer.keys())

    LR = layout.direction in ("LR", "RL")
    reverse_main = layout.direction in ("RL", "BT")
    S = len(order)

    for si, L in enumerate(order):
        main_t = 0.1 + 0.8 * (si / max(1, S - 1)) if S > 1 else 0.5
        row = by_layer[L]
        # сортировка в слое по среднему положению предков (для минимизации пересечений — грубо)
        pos_index = {bid: j for j, bid in enumerate(by_layer[order[si-1]])} if si > 0 else {}
        row.sort(key=lambda b: sum(pos_index.get(p, 0) for p in incoming.get(b, [])) / max(1, len(incoming.get(b, []))))
        m = len(row)
        for j, bid in enumerate(row):
            b = next(bb for bb in blocks if bb.id == bid)
            if b.pos is not None and layout.respect_fixed_blocks:
                continue
            perp = 0.2 + 0.6 * (j / max(1, m - 1)) if m > 1 else 0.5
            x, y = (main_t, perp) if LR else (perp, main_t)
            if reverse_main:
                if LR: x = 1.0 - x
                else:  y = 1.0 - y
            b.auto_pos = (clamp01(x), clamp01(y))

# ----------------- render -----------------

def block_xywh(b: Block, W: int, H: int, d: Defaults):
    pos = b.eff_pos() or (0.5, 0.5)
    w = max(1.0, b.eff_width(d) * W)
    hh = b.eff_header(d) * H
    ph = b.eff_prop(d) * H
    total_h = hh + ph * max(0, len(b.properties))
    h = max(1.0, total_h)
    cx, cy = pos[0] * W, pos[1] * H
    x, y = cx - w/2, cy - h/2
    # сохраним для стрелок
    b.cx_px, b.cy_px, b.w_px, b.h_px = cx, cy, w, h
    return x, y, w, h, hh, ph

def connector_point(b: Block, side: str):
    side = (side or 'center').lower()
    if side == 'side':
        # трактуем 'side' как правый край по умолчанию
        side = 'right'
    x = b.cx_px - b.w_px/2
    y = b.cy_px - b.h_px/2
    if side == "left":   return (x, b.cy_px)
    if side == "right":  return (x + b.w_px, b.cy_px)
    if side == "top":    return (b.cx_px, y)
    if side == "bottom": return (b.cx_px, y + b.h_px)
    return (b.cx_px, b.cy_px)

def choose_side(p1, p2, pref: str):
    pref = (pref or "auto").lower()
    if pref != "auto":
        return pref
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    if abs(dx) >= abs(dy):
        return "right" if dx >= 0 else "left"
    else:
        return "bottom" if dy >= 0 else "top"

def render_svg(di: dict, cfg: dict, out_svg: Path):
    # конфиг
    io = cfg.get("io", {})
    defaults = Defaults(cfg.get("defaults", {}))
    layout = LayoutCfg(cfg.get("layout", {}))
    style = defaults  # используем поля из defaults для стилей

    # холст
    W, H = defaults.canvas_size
    meta = di.get("meta", {}) or {}
    if isinstance(meta.get("canvas_size"), list) and len(meta["canvas_size"]) == 2:
        W, H = int(meta["canvas_size"][0]), int(meta["canvas_size"][1])

    # блоки
    raw_blocks = di.get("blocks", []) or []
    blocks = [Block(rb, i) for i, rb in enumerate(raw_blocks)]

    # fallback layout: если pos/auto_pos нет — разложить слоями
    layered_layout(blocks, [], layout)

    parts = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{style.theme_background}"/>')

    title = str(meta.get("title") or "")
    if title:
        parts.append(
            f'<text x="{W/2:.1f}" y="24" text-anchor="middle" '
            f'font-family="{style.font_family}" font-size="{style.font_size_title+2}" '
            f'fill="{style.theme_text}" font-weight="bold">{svg_escape(title)}</text>'
        )

    # рисуем блоки
    for b in blocks:
        x, y, w, h, HH, PH = block_xywh(b, W, H, defaults)
        shape = b.eff_shape(defaults)
        rr = b.eff_corner_radius(defaults)
        stroke_w = b.eff_stroke_width(defaults)
        fill = b.eff_fill(defaults)
        stroke = b.eff_stroke(defaults)

        if shape in ("rect","rounded","pill"):
            rx = rr if shape != "rect" else 0
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" rx="{rx}" ry="{rx}" width="{w:.1f}" height="{h:.1f}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>')
        elif shape == "ellipse":
            parts.append(f'<ellipse cx="{b.cx_px:.1f}" cy="{b.cy_px:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>')
        else:
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                         f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>')

        # разделитель шапки
        parts.append(f'<line x1="{x:.1f}" y1="{y+HH:.1f}" x2="{x+w:.1f}" y2="{y+HH:.1f}" '
                     f'stroke="{stroke}" stroke-width="{max(1.0, stroke_w/2)}"/>')

        # заголовок
        fw = "bold" if b.eff_font_bold_title(defaults) else "normal"
        ffam = b.eff_font_family(defaults)
        fsize_t = b.eff_font_size_title(defaults)
        ta = b.eff_text_align_title(defaults).lower()   # left|center|right
        tanchor = "start" if ta=="left" else ("end" if ta=="right" else "middle")
        dax = b.eff_text_pad_title_x(defaults)
        day = b.eff_text_pad_title_y(defaults)
        if tanchor == "start":
            tx = x + dax
        elif tanchor == "end":
            tx = x + w - dax
        else:
            tx = x + w/2
        tv = b.eff_text_valign_title(defaults).lower()  # baseline|middle
        if tv == "middle":
            ty = y + HH/2; dom = ' dominant-baseline="middle"'
        else:
            ty = y + HH - day; dom = ''
        parts.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{tanchor}"{dom} '
                     f'font-family="{ffam}" font-size="{fsize_t}" fill="{style.theme_text}" font-weight="{fw}">'
                     f'{svg_escape(b.title)}</text>')

        # свойства + разделители
        fsize_p = b.eff_font_size_prop(defaults)
        ta2 = b.eff_text_align_props(defaults).lower()
        tanchor2 = "start" if ta2=="left" else ("end" if ta2=="right" else "middle")
        pax = b.eff_text_pad_prop_x(defaults)
        pay = b.eff_text_pad_prop_y(defaults)
        if tanchor2 == "start":
            px = x + pax
        elif tanchor2 == "end":
            px = x + w - pax
        else:
            px = x + w/2
        tv2 = b.eff_text_valign_props(defaults).lower()
        dom2 = ' dominant-baseline="middle"' if tv2 == "middle" else ''
        for i, prop in enumerate(b.properties):
            parts.append(f'<line x1="{x:.1f}" y1="{y+HH+PH*i:.1f}" x2="{x+w:.1f}" y2="{y+HH+PH*i:.1f}" '
                         f'stroke="{stroke}" stroke-width="{max(0.5, stroke_w/2.5)}"/>')
            if tv2 == "middle":
                py = y + HH + PH*i + PH/2
            else:
                py = y + HH + PH*(i+1) - pay
            parts.append(f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{tanchor2}"{dom2} '
                         f'font-family="{ffam}" font-size="{fsize_p}" fill="{style.theme_text}">{svg_escape(prop)}</text>')

    # стрелки
    id2b = {b.id: b for b in blocks}
    arrow_color = style.theme_arrow
    stroke_w = max(1.0, style.style_arrow_thickness)
    arrow_len = 6 * max(0.5, style.style_arrow_size)

    def draw_arrow(p1, p2, curve: str):
        if curve == "straight":
            return f'M {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        if curve == "orthogonal":
            # одна коленка — ориентируемся на доминирующую ось
            mid = (p2[0], p1[1]) if abs(p2[0]-p1[0]) > abs(p2[1]-p1[1]) else (p1[0], p2[1])
            return f'M {p1[0]:.1f},{p1[1]:.1f} L {mid[0]:.1f},{mid[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        # auto => orthogonal (без spline)
        mid = (p2[0], p1[1]) if abs(p2[0]-p1[0]) > abs(p2[1]-p1[1]) else (p1[0], p2[1])
        return f'M {p1[0]:.1f},{p1[1]:.1f} L {mid[0]:.1f},{mid[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'

    def arrow_head(p1, p2):
        ang = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
        a1, a2 = ang - math.pi/7, ang + math.pi/7
        x1, y1 = p2[0] - arrow_len*math.cos(a1), p2[1] - arrow_len*math.sin(a1)
        x2, y2 = p2[0] - arrow_len*math.cos(a2), p2[1] - arrow_len*math.sin(a2)
        return f'M {p2[0]:.1f},{p2[1]:.1f} L {x1:.1f},{y1:.1f} M {p2[0]:.1f},{p2[1]:.1f} L {x2:.1f},{y2:.1f}'

    for b in blocks:
        for o in b.outs:
            to_id = o.get("to")
            if to_id not in id2b:
                continue
            tgt = id2b[to_id]
            s1 = choose_side((b.cx_px,b.cy_px),(tgt.cx_px,tgt.cy_px), (o.get("style.connector_from") or style.style_connector_from))
            s2 = choose_side((tgt.cx_px,tgt.cy_px),(b.cx_px,b.cy_px), (o.get("style.connector_to") or style.style_connector_to))
            p1 = connector_point(b, s1); p2 = connector_point(tgt, s2)
            curve = (o.get("style.curve") or style.style_curve or "auto")
            if curve == "spline": curve = "orthogonal"  # принудительно без spline
            d_path = draw_arrow(p1, p2, curve)
            parts.append(f'<path d="{d_path}" fill="none" stroke="{arrow_color}" stroke-width="{stroke_w}"/>')
            parts.append(f'<path d="{arrow_head(p1,p2)}" stroke="{arrow_color}" stroke-width="{max(1.0, stroke_w-0.5)}"/>' )

            label = o.get("label")
            if label:
                t = float((o.get("style.label_offset") if o.get("style.label_offset") is not None else style.style_label_offset) or 0.5)
                t = max(0.0, min(1.0, t))
                lx = p1[0] + (p2[0]-p1[0]) * t
                ly = p1[1] + (p2[1]-p1[1]) * t - 4
                font_style = "italic" if style.font_italic_arrow else "normal"
                parts.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                             f'font-family="{style.font_family}" font-size="{style.font_size_prop}" '
                             f'fill="{arrow_color}" font-style="{font_style}">{svg_escape(label)}</text>')

    parts.append("</svg>")
    svg = "\n".join(parts)
    out_svg.write_text(svg, encoding="utf-8")
    return svg

# ----------------- main -----------------

def main():
    cfg_path = Path(__file__).with_name("config_render.toml")
    if not cfg_path.exists():
        print(f"ERR: config not found: {cfg_path}")
        sys.exit(2)
    cfg = read_toml(cfg_path)

    io = cfg.get("io", {})
    input_dirs = io.get("input_dirs", [])
    recursive = bool(io.get("recursive", True))
    input_suffix = str(io.get("input_suffix", "_02.toml"))
    include_exts = io.get("include_extensions", ["toml"])
    exclude_patterns = io.get("exclude_patterns", [])
    output_suffix = str(io.get("output_suffix", "_03"))
    dry_run = bool(io.get("dry_run", False))
    save_png = bool(cfg.get("output", {}).get("save_png", False))
    png_dpi = int(cfg.get("output", {}).get("png_dpi", 200))

    files = discover_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns)
    print(f"Found {len(files)} file(s).")

    total_ok = 0
    for src in files:
        try:
            g = read_toml(src)
            base = src.name[:-5] if src.name.endswith(".toml") else src.stem
            out_svg = src.with_name(base + output_suffix + ".svg")
            if dry_run:
                print(f"DRY-RUN: would render -> {out_svg}")
            else:
                svg = render_svg(g, cfg, out_svg)
                print(f"SVG: {out_svg.name}")
                if save_png:
                    try:
                        import cairosvg
                        out_png = src.with_name(base + output_suffix + ".png")
                        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_png), dpi=png_dpi)
                        print(f"PNG: {out_png.name} (dpi={png_dpi})")
                    except Exception as e:
                        print("WARN: PNG экспорт не выполнен:", e)
            total_ok += 1
        except Exception as e:
            print(f"ERR rendering {src}: {e}")
            sys.exit(1)
    print(f"Done. Rendered: {total_ok}")

if __name__ == "__main__":
    main()
