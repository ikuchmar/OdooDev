#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
draw_graph.py — ПРОСТАЯ и ПОНЯТНАЯ версия
-----------------------------------------

Что делает:
1) Читает рядом лежащий run.toml (файл настроек).
2) Находит TOML-файлы графов по папкам (input_dirs).
3) Для каждого графа:
   - читает blocks/arrows;
   - вычисляет раскладку (по слоям слева-направо — "layered");
   - аккуратно «разводит» блоки внутри слоёв, чтобы НЕ наслаивались;
   - переводит нормированные размеры в пиксели;
   - рисует SVG (и PNG, если есть cairosvg);
   - сохраняет рассчитанные позиции и, при желании, размеры прямо в [[blocks]];
   - также обновляет [layout_result.blocks_pos] в конце файла.

Ключевые идеи:
- Размеры блока НОРМИРОВАНЫ (0..1) относительно холста:
    ширина   = block.width        * canvas_width
    высота   = (header_height + prop_height*len(properties)) * canvas_height
- Центр блока pos = [x, y] также НОРМИРОВАНЫ (0..1).
- Чтобы подпись стрелки была по центру — [defaults].style.label_offset = 0.5.

ВАЖНО:
- Здесь максимум простоты: минимум "магии", больше прямых шагов и комментариев.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Чтение TOML: в Python 3.11+ есть stdlib "tomllib"
try:
    import tomllib  # type: ignore
except Exception as e:
    print("ERROR: Нужен Python 3.11+ (модуль tomllib).", e)
    sys.exit(1)

# PNG-экспорт (не обязателен). Если установлен cairosvg — сделаем PNG.
_HAS_CAIROSVG = False
try:
    import cairosvg  # type: ignore
    _HAS_CAIROSVG = True
except Exception:
    pass


# ---------------------------
# Небольшие служебные функции
# ---------------------------

def clamp01(x: float) -> float:
    """Ограничить число на отрезке [0..1]."""
    return max(0.0, min(1.0, x))

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def make_backup(src: Path) -> None:
    """Создать .bak перед записью изменений."""
    bak = src.with_suffix(src.suffix + ".bak")
    shutil.copy2(src, bak)

def round_to_grid(x: float, step: float) -> float:
    """Привязать значение к сетке (например, шаг 0.01 — кратно 1%)."""
    if step <= 0:
        return x
    return round(x / step) * step


# ---------------------
# Структуры настроек
# ---------------------

@dataclass
class Defaults:
    canvas_size: Tuple[int, int] = (1200, 800)

    # Глобальные стили рёбер/подписей
    style_curve: str = "auto"            # auto|straight|arc|spline
    style_label_offset: float = 0.5      # 0..1
    style_connector_from: str = "auto"   # auto|left|right|top|bottom
    style_connector_to: str = "auto"     # auto|left|right|top|bottom
    style_arrow_size: float = 1.0
    style_arrow_thickness: float = 2.0

    # Габариты блоков (нормированные)
    block_width: float = 0.22
    block_header_height: float = 0.12
    block_prop_height: float = 0.06

    # Оформление блоков/текста
    block_corner_radius: float = 10.0
    block_stroke_width: float = 2.0
    block_fill_color: str = "none"
    block_stroke_color: str = "#000000"

    font_family: str = "Arial"
    font_size_title: int = 14
    font_size_prop: int = 12
    font_size_arrow: int = 11
    font_bold_title: bool = True
    font_italic_arrow: bool = True

    # Тема
    theme_background: str = "#FFFFFF"
    theme_text_color: str = "#000000"
    theme_arrow_color: str = "#222222"
    theme_block_fill_color: str = "none"
    theme_block_stroke_color: str = "#000000"


@dataclass
class LayoutCfg:
    mode: str = "layered"        # layered|force|off
    direction: str = "LR"        # LR|RL|TB|BT
    minimize_edge_crossings: bool = True
    avoid_node_overlap: bool = True
    edge_routing: str = "orthogonal"     # straight|orthogonal|spline|auto
    edge_label_placement: str = "smart"  # smart|center
    node_padding: float = 0.02
    grid_snap: float = 0.01
    deterministic: bool = True
    seed: int = 42
    respect_fixed_blocks: bool = True
    iterations: int = 500
    layer_gap: float = 0.08
    node_gap: float = 0.03


@dataclass
class PersistCfg:
    write_positions_to_input: bool = True
    write_mode: str = "overwrite"          # overwrite|update_missing
    sort_blocks: str = "by_pos_id"         # by_pos_id|by_id
    sort_arrows: str = "by_from_to_label"  # by_from_to_label|none
    create_backup: bool = True

    # Новое: писать геометрию прямо в [[blocks]]
    write_block_geometry: bool = True
    persist_geometry_fields: List[str] = field(default_factory=lambda: ["pos", "width", "header_height", "prop_height"])


@dataclass
class OutputCfg:
    save_png: bool = True
    save_svg: bool = True
    png_dpi: int = 200
    file_naming: str = "same_basename"
    open_in_browser: str = "svg"    # none|svg|html (используем только svg)
    show_preview_windows: bool = False


@dataclass
class RunConfig:
    input_dirs: List[str] = field(default_factory=list)
    recursive: bool = True
    include_extensions: List[str] = field(default_factory=lambda: ["toml"])
    exclude_patterns: List[str] = field(default_factory=list)

    layout: LayoutCfg = field(default_factory=LayoutCfg)
    persist: PersistCfg = field(default_factory=PersistCfg)
    output: OutputCfg = field(default_factory=OutputCfg)
    defaults: Defaults = field(default_factory=Defaults)


# ---------------------
# Данные графа
# ---------------------

@dataclass
class Block:
    id: str
    title: str
    properties: List[str]
    pos: Optional[Tuple[float, float]] = None   # нормированные координаты центра (0..1)
    width: Optional[float] = None               # нормированная ширина
    header_height: Optional[float] = None       # нормированная высота шапки
    prop_height: Optional[float] = None         # нормированная высота строки свойства

    # Вычисляемые пиксельные значения:
    w_px: float = 0.0
    h_px: float = 0.0
    cx_px: float = 0.0
    cy_px: float = 0.0

    def normalized_size(self, defs: Defaults) -> Tuple[float, float]:
        """Вернуть (ширина, высота) в НОРМИРОВАННЫХ величинах (0..1)."""
        w = self.width if self.width is not None else defs.block_width
        hh = self.header_height if self.header_height is not None else defs.block_header_height
        ph = self.prop_height if self.prop_height is not None else defs.block_prop_height
        total_h = hh + ph * max(0, len(self.properties))
        return (w, total_h)


@dataclass
class Arrow:
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: Dict[str, object] = field(default_factory=dict)  # локальные style.* (опционально)


@dataclass
class Diagram:
    meta: Dict[str, object]
    blocks: List[Block]
    arrows: List[Arrow]


# --------------------------
# Чтение run.toml и графов
# --------------------------

def load_run_config(path: Path) -> RunConfig:
    """Прочитать run.toml (все секции) в удобные dataclass-ы."""
    cfg_raw = tomllib.loads(read_text(path))
    def get(d, k, default=None):
        return d.get(k, default) if isinstance(d, dict) else default

    rc = RunConfig()
    # Верхний уровень
    rc.input_dirs = cfg_raw.get("input_dirs", [])
    rc.recursive = cfg_raw.get("recursive", True)
    rc.include_extensions = cfg_raw.get("include_extensions", ["toml"])
    rc.exclude_patterns = cfg_raw.get("exclude_patterns", [])

    # layout
    L = cfg_raw.get("layout", {})
    rc.layout = LayoutCfg(
        mode=get(L, "mode", "layered"),
        direction=get(L, "direction", "LR"),
        minimize_edge_crossings=get(L, "minimize_edge_crossings", True),
        avoid_node_overlap=get(L, "avoid_node_overlap", True),
        edge_routing=get(L, "edge_routing", "orthogonal"),
        edge_label_placement=get(L, "edge_label_placement", "smart"),
        node_padding=float(get(L, "node_padding", 0.02)),
        grid_snap=float(get(L, "grid_snap", 0.01)),
        deterministic=get(L, "deterministic", True),
        seed=int(get(L, "seed", 42)),
        respect_fixed_blocks=get(L, "respect_fixed_blocks", True),
        iterations=int(get(L, "iterations", 500)),
        layer_gap=float(get(L, "layer_gap", 0.08)),
        node_gap=float(get(L, "node_gap", 0.03)),
    )

    # persist
    P = cfg_raw.get("persist", {})
    rc.persist = PersistCfg(
        write_positions_to_input=get(P, "write_positions_to_input", True),
        write_mode=get(P, "write_mode", "overwrite"),
        sort_blocks=get(P, "sort_blocks", "by_pos_id"),
        sort_arrows=get(P, "sort_arrows", "by_from_to_label"),
        create_backup=get(P, "create_backup", True),
        write_block_geometry=get(P, "write_block_geometry", True),
        persist_geometry_fields=get(P, "persist_geometry_fields", ["pos","width","header_height","prop_height"]),
    )

    # output
    O = cfg_raw.get("output", {})
    rc.output = OutputCfg(
        save_png=get(O, "save_png", True),
        save_svg=get(O, "save_svg", True),
        png_dpi=int(get(O, "png_dpi", 200)),
        file_naming=get(O, "file_naming", "same_basename"),
        open_in_browser=get(O, "open_in_browser", "svg"),
        show_preview_windows=get(O, "show_preview_windows", False),
    )

    # defaults
    D = cfg_raw.get("defaults", {})
    rc.defaults = Defaults(
        canvas_size=tuple(get(D, "canvas_size", [1200, 800])),
        style_curve=get(D, "style.curve", "auto"),
        style_label_offset=float(get(D, "style.label_offset", 0.5)),
        style_connector_from=get(D, "style.connector_from", "auto"),
        style_connector_to=get(D, "style.connector_to", "auto"),
        style_arrow_size=float(get(D, "style.arrow_size", 1.0)),
        style_arrow_thickness=float(get(D, "style.arrow_thickness", 2.0)),
        block_width=float(get(D, "block.width", 0.22)),
        block_header_height=float(get(D, "block.header_height", 0.12)),
        block_prop_height=float(get(D, "block.prop_height", 0.06)),
        block_corner_radius=float(get(D, "block.corner_radius", 10.0)),
        block_stroke_width=float(get(D, "block.stroke_width", 2.0)),
        block_fill_color=get(D, "block.fill_color", "none"),
        block_stroke_color=get(D, "block.stroke_color", "#000000"),
        font_family=get(D, "font.family", "Arial"),
        font_size_title=int(get(D, "font.size_title", 14)),
        font_size_prop=int(get(D, "font.size_prop", 12)),
        font_size_arrow=int(get(D, "font.size_arrow", 11)),
        font_bold_title=bool(get(D, "font.bold_title", True)),
        font_italic_arrow=bool(get(D, "font.italic_arrow", True)),
        theme_background=get(D, "theme.background", "#FFFFFF"),
        theme_text_color=get(D, "theme.text_color", "#000000"),
        theme_arrow_color=get(D, "theme.arrow_color", "#222222"),
        theme_block_fill_color=get(D, "theme.block_fill_color", "none"),
        theme_block_stroke_color=get(D, "theme.block_stroke_color", "#000000"),
    )
    return rc


def parse_diagram(path: Path) -> Diagram:
    """Прочитать один TOML-граф (blocks/arrows + meta)."""
    raw = read_text(path)
    data = tomllib.loads(raw)
    meta = data.get("meta", {})
    blocks_raw = data.get("blocks", []) or []
    arrows_raw = data.get("arrows", []) or []
    layout_result = data.get("layout_result", {})
    saved = {}
    if isinstance(layout_result, dict):
        saved = layout_result.get("blocks_pos", {}) or {}

    # Сборка блоков
    blocks: List[Block] = []
    seen = set()
    for b in blocks_raw:
        bid = b.get("id")
        if not bid or bid in seen:
            raise ValueError(f"Дублированный или отсутствующий id блока в {path}")
        seen.add(bid)

        # pos можно взять из [[blocks]] (приоритет) или из [layout_result.blocks_pos]
        pos = b.get("pos")
        if pos is None and bid in saved:
            pos = saved[bid]
        if pos is not None:
            pos = (float(pos[0]), float(pos[1]))

        blocks.append(Block(
            id=bid,
            title=b.get("title", ""),
            properties=list(b.get("properties", [])),
            pos=pos,
            width=b.get("width"),
            header_height=b.get("header_height"),
            prop_height=b.get("prop_height"),
        ))

    # Сборка стрелок
    arrows: List[Arrow] = []
    for a in arrows_raw:
        frm, to = a.get("from"), a.get("to")
        if not frm or not to:
            raise ValueError(f"Стрелка без from/to в {path}")
        # Собираем только известные style.* (остальное игнорируем)
        style = {}
        for key in ("style.curve", "style.label_offset", "style.connector_from", "style.connector_to"):
            if key in a:
                style[key] = a[key]
        arrows.append(Arrow(from_id=frm, to_id=to, label=a.get("label"), style=style))

    return Diagram(meta=meta, blocks=blocks, arrows=arrows)


# --------------------
# Раскладка (layered)
# --------------------

def layered_layout(di: Diagram, rc: RunConfig) -> None:
    """
    Простейшая "layered"-раскладка слева-направо:
    - определяем слои по расстоянию от "истоков" (узлов без входящих рёбер);
    - равномерно раскладываем слои по оси X (для LR);
    - внутри слоя равномерно раскладываем блоки по оси Y;
    - ПРИМЕЧАНИЕ: здесь мы задаём ТОЛЬКО pos (нормированные),
      а фактические пиксельные размеры учтём позже при "разводке" без наложений.
    """
    direction = (rc.layout.direction or "LR").upper()
    left_to_right = direction in ("LR", "RL")
    reverse_main = direction in ("RL", "BT")

    # Строим списки входящих/исходящих
    incoming: Dict[str, List[str]] = {b.id: [] for b in di.blocks}
    outgoing: Dict[str, List[str]] = {b.id: [] for b in di.blocks}
    ids = {b.id for b in di.blocks}
    for a in di.arrows:
        if a.from_id in ids and a.to_id in ids:
            outgoing[a.from_id].append(a.to_id)
            incoming[a.to_id].append(a.from_id)

    # Истоки — кто без входящих:
    sources = [bid for bid, inc in incoming.items() if not inc] or ([di.blocks[0].id] if di.blocks else [])

    # BFS по слоям
    layer_of = {bid: math.inf for bid in ids}
    for s in sources:
        layer_of[s] = 0
    frontier = list(sources)
    while frontier:
        new_frontier = []
        for u in frontier:
            for v in outgoing.get(u, []):
                if layer_of[v] > layer_of[u] + 1:
                    layer_of[v] = layer_of[u] + 1
                    new_frontier.append(v)
        frontier = new_frontier

    # Не достигнутые — отправим в следующие слои
    max_layer = max([0] + [d for d in layer_of.values() if d < math.inf])
    for bid, lv in list(layer_of.items()):
        if lv == math.inf:
            max_layer += 1
            layer_of[bid] = max_layer

    # Собираем слои
    layers: Dict[int, List[str]] = {}
    for bid, lv in layer_of.items():
        layers.setdefault(int(lv), []).append(bid)

    order_layers = sorted(layers.keys())
    if reverse_main:
        order_layers = list(reversed(order_layers))

    # Упорядочим внутри слоя (простая эвристика по среднему индексу соседей)
    for idx, L in enumerate(order_layers):
        row = layers[L]
        # Посмотрим на соседний слой слева
        if idx > 0:
            left_ids = layers[order_layers[idx-1]]
            pos_index = {bid: i for i, bid in enumerate(left_ids)}
            row.sort(key=lambda b: sum(pos_index.get(p, 0) for p in incoming.get(b, [])) / max(1, len(incoming.get(b, []))))
        layers[L] = row

    # Присвоим pos (нормированные)
    S = len(order_layers)
    for si, L in enumerate(order_layers):
        # главная ось (X при LR): от 0.1 до 0.9
        main_t = 0.1 + 0.8 * (si / max(1, S - 1)) if S > 1 else 0.5
        row = layers[L]
        m = len(row)
        for j, bid in enumerate(row):
            b = next(bb for bb in di.blocks if bb.id == bid)
            # фиксированные pos (если respect_fixed_blocks) — не трогаем
            if b.pos is not None and rc.layout.respect_fixed_blocks:
                continue
            # перпендикулярная ось: равномерно от 0.2 до 0.8 (чтобы был запас сверху/снизу)
            perp_t = 0.2 + 0.6 * (j / max(1, m - 1)) if m > 1 else 0.5
            x, y = (main_t, perp_t) if left_to_right else (perp_t, main_t)
            if reverse_main:
                if left_to_right:
                    x = 1.0 - x
                else:
                    y = 1.0 - y
            b.pos = (clamp01(x), clamp01(y))


# -----------------------------------
# Перевод нормированных величин в px
# -----------------------------------

def compute_pixel_geometry(di: Diagram, defs: Defaults) -> Tuple[int, int]:
    """Заполнить для каждого блока w_px, h_px, cx_px, cy_px. Вернуть (W,H)."""
    W, H = defs.canvas_size
    # meta.canvas_size может переопределить глобальный холст
    meta_cs = di.meta.get("canvas_size")
    if isinstance(meta_cs, list) and len(meta_cs) == 2:
        W, H = int(meta_cs[0]), int(meta_cs[1])

    for b in di.blocks:
        w_norm, h_norm = b.normalized_size(defs)
        b.w_px = w_norm * W
        b.h_px = h_norm * H
        cx, cy = b.pos if b.pos is not None else (0.5, 0.5)
        b.cx_px = cx * W
        b.cy_px = cy * H
    return W, H


# --------------------------------------------
# Простая «разводка» без наложения блоков
# --------------------------------------------

def resolve_overlaps_by_layers(di: Diagram, rc: RunConfig, W: int, H: int) -> None:
    """
    После первичной раскладки (pos) и пересчёта в пиксели — разводим блоки, чтобы
    они не залезали друг на друга. Работаем по «слоям» (главная ось) и по
    перпендикулярной оси (внутри слоя).
    """
    LR = (rc.layout.direction or "LR").upper() in ("LR", "RL")

    # 1) Разобьём на слои по близости главной координаты (cx для LR; cy для TB/BT)
    blocks = list(di.blocks)
    blocks.sort(key=(lambda b: b.cx_px) if LR else (lambda b: b.cy_px))

    # Порог «слияния в слой» по главной оси
    layer_thresh_px = (rc.layout.layer_gap if rc.layout.layer_gap > 0 else 0.08) * (W if LR else H)

    layers: List[List[Block]] = []
    cur: List[Block] = []
    last_main = None
    for b in blocks:
        m = b.cx_px if LR else b.cy_px
        if last_main is None or abs(m - last_main) <= layer_thresh_px:
            cur.append(b)
            last_main = m if last_main is None else (last_main + m) / 2
        else:
            layers.append(cur)
            cur = [b]
            last_main = m
    if cur:
        layers.append(cur)

    # 2) В каждом слое разложим по перпендикулярной оси с зазором
    node_gap_px = (rc.layout.node_gap if rc.layout.node_gap > 0 else 0.03) * (H if LR else W)

    for row in layers:
        if LR:
            # Работаем по вертикали (Y). Сортируем по текущему Y.
            row.sort(key=lambda b: b.cy_px)
            top, bottom = 0.10 * H, 0.90 * H
            for i, b in enumerate(row):
                if i == 0:
                    b.cy_px = max(top + b.h_px/2, min(b.cy_px, bottom - b.h_px/2))
                else:
                    prev = row[i - 1]
                    min_y = prev.cy_px + prev.h_px/2 + node_gap_px + b.h_px/2
                    b.cy_px = max(b.cy_px, min_y)
                    if b.cy_px + b.h_px/2 > bottom:
                        b.cy_px = bottom - b.h_px/2
            # Обратный проход, чтобы слой целиком «влез» в коридор
            for i in range(len(row) - 2, -1, -1):
                cur_b = row[i]
                nxt = row[i + 1]
                max_y = nxt.cy_px - nxt.h_px/2 - node_gap_px - cur_b.h_px/2
                cur_b.cy_px = min(cur_b.cy_px, max_y)
                if cur_b.cy_px - cur_b.h_px/2 < top:
                    cur_b.cy_px = top + cur_b.h_px/2
        else:
            # TB/BT — работаем по горизонтали (X)
            row.sort(key=lambda b: b.cx_px)
            left, right = 0.10 * W, 0.90 * W
            for i, b in enumerate(row):
                if i == 0:
                    b.cx_px = max(left + b.w_px/2, min(b.cx_px, right - b.w_px/2))
                else:
                    prev = row[i - 1]
                    min_x = prev.cx_px + prev.w_px/2 + node_gap_px + b.w_px/2
                    b.cx_px = max(b.cx_px, min_x)
                    if b.cx_px + b.w_px/2 > right:
                        b.cx_px = right - b.w_px/2
            for i in range(len(row) - 2, -1, -1):
                cur_b = row[i]
                nxt = row[i + 1]
                max_x = nxt.cx_px - nxt.w_px/2 - node_gap_px - cur_b.w_px/2
                cur_b.cx_px = min(cur_b.cx_px, max_x)
                if cur_b.cx_px - cur_b.w_px/2 < left:
                    cur_b.cx_px = left + cur_b.w_px/2

    # 3) «Страховка»: поджать ВСЕ блоки внутрь холста, с полем 2% по краям
    edge_pad = 0.02
    min_x = edge_pad * W
    max_x = (1.0 - edge_pad) * W
    min_y = edge_pad * H
    max_y = (1.0 - edge_pad) * H

    for b in di.blocks:
        b.cx_px = max(min_x + b.w_px/2, min(b.cx_px, max_x - b.w_px/2))
        b.cy_px = max(min_y + b.h_px/2, min(b.cy_px, max_y - b.h_px/2))

    # Обратно в нормированные pos (для записи)
    for b in di.blocks:
        b.pos = (clamp01(b.cx_px / W), clamp01(b.cy_px / H))


# -----------------
# Рендер SVG (простой)
# -----------------

def svg_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def block_bbox(b: Block) -> Tuple[float, float, float, float]:
    """Вернуть левый верхний угол (x,y) и (w,h) блока в пикселях."""
    x = b.cx_px - b.w_px / 2
    y = b.cy_px - b.h_px / 2
    return x, y, b.w_px, b.h_px

def render_svg(di: Diagram, defs: Defaults, out_svg: Path) -> str:
    """Нарисовать простой SVG-файл (прямоугольники блоков, линии-стрелки, подписи)."""
    W, H = defs.canvas_size
    meta_cs = di.meta.get("canvas_size")
    if isinstance(meta_cs, list) and len(meta_cs) == 2:
        W, H = int(meta_cs[0]), int(meta_cs[1])

    # Цвета и оформление
    bg = defs.theme_background
    text_color = defs.theme_text_color
    arrow_color = defs.theme_arrow_color
    block_fill = defs.block_fill_color if defs.block_fill_color != "none" else defs.theme_block_fill_color
    block_stroke = defs.block_stroke_color if defs.block_stroke_color != "#000000" else defs.theme_block_stroke_color

    parts: List[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>')

    # Заголовок диаграммы (если есть)
    title = str(di.meta.get("title") or "")
    if title:
        parts.append(
            f'<text x="{W/2:.1f}" y="24" text-anchor="middle" '
            f'font-family="{defs.font_family}" font-size="{defs.font_size_title+2}" '
            f'fill="{text_color}" font-weight="bold">{svg_escape(title)}</text>'
        )

    # Сначала блоки (прямоугольники + шапка + свойства)
    for b in di.blocks:
        x, y, w, h = block_bbox(b)
        rr = defs.block_corner_radius
        # Рамка блока
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" rx="{rr}" ry="{rr}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{block_fill}" stroke="{block_stroke}" stroke-width="{defs.block_stroke_width}"/>'
        )
        # Горизонтальная линия под шапкой
        header_h_px = (b.header_height if b.header_height is not None else defs.block_header_height) * H
        parts.append(
            f'<line x1="{x:.2f}" y1="{y+header_h_px:.2f}" x2="{x+w:.2f}" y2="{y+header_h_px:.2f}" '
            f'stroke="{block_stroke}" stroke-width="{max(1.0, defs.block_stroke_width/2)}"/>'
        )
        # Текст заголовка в шапке
        fw = "bold" if defs.font_bold_title else "normal"
        parts.append(
            f'<text x="{x+6:.1f}" y="{y + header_h_px - 6:.1f}" '
            f'font-family="{defs.font_family}" font-size="{defs.font_size_title}" '
            f'fill="{text_color}" font-weight="{fw}">{svg_escape(b.title)}</text>'
        )
        # Строки свойств
        prop_h_px = (b.prop_height if b.prop_height is not None else defs.block_prop_height) * H
        for i, prop in enumerate(b.properties):
            yy = y + header_h_px + prop_h_px * i
            # Разделительная линия над строкой
            parts.append(
                f'<line x1="{x:.2f}" y1="{yy:.2f}" x2="{x+w:.2f}" y2="{yy:.2f}" '
                f'stroke="{block_stroke}" stroke-width="{max(0.5, defs.block_stroke_width/2.5)}"/>'
            )
            # Текст свойства
            parts.append(
                f'<text x="{x+6:.1f}" y="{yy + prop_h_px - 6:.1f}" '
                f'font-family="{defs.font_family}" font-size="{defs.font_size_prop}" '
                f'fill="{text_color}">{svg_escape(prop)}</text>'
            )

    # Затем рисуем стрелки поверх (упрощённо)
    def effective_style(a: Arrow) -> Dict[str, object]:
        # базово — из defaults
        es = {
            "curve": defs.style_curve,
            "label_offset": defs.style_label_offset,
            "connector_from": defs.style_connector_from,
            "connector_to": defs.style_connector_to,
        }
        # поверх — точечные переопределения в стрелке (style.*)
        for k, v in a.style.items():
            es[k.split("style.", 1)[-1]] = v
        return es

    id2b = {b.id: b for b in di.blocks}

    def connector_point(b: Block, side: str) -> Tuple[float, float]:
        """Вернуть точку на границе блока в зависимости от стороны."""
        x, y, w, h = block_bbox(b)
        if side == "left":
            return (x, y + h / 2)
        if side == "right":
            return (x + w, y + h / 2)
        if side == "top":
            return (x + w / 2, y)
        if side == "bottom":
            return (x + w / 2, y + h)
        # auto — выберем сторону по направлению
        return (b.cx_px, b.cy_px)

    def choose_side(p_from: Tuple[float, float], p_to: Tuple[float, float], pref: str) -> str:
        if pref != "auto":
            return pref
        dx, dy = p_to[0] - p_from[0], p_to[1] - p_from[1]
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        else:
            return "bottom" if dy >= 0 else "top"

    for a in di.arrows:
        if a.from_id not in id2b or a.to_id not in id2b:
            continue
        b1, b2 = id2b[a.from_id], id2b[a.to_id]
        st = effective_style(a)

        side_from = choose_side((b1.cx_px, b1.cy_px), (b2.cx_px, b2.cy_px), st["connector_from"])
        side_to   = choose_side((b2.cx_px, b2.cy_px), (b1.cx_px, b1.cy_px), st["connector_to"])

        p1 = connector_point(b1, side_from)
        p2 = connector_point(b2, side_to)

        # Рисуем линию/ломаную/кривую
        curve = st["curve"]
        if curve == "straight":
            d = f'M {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        elif curve == "orthogonal":
            # простая «угловая» линия: через промежуточную точку
            mid = (p2[0], p1[1]) if abs(p2[0]-p1[0]) > abs(p2[1]-p1[1]) else (p1[0], p2[1])
            d = f'M {p1[0]:.1f},{p1[1]:.1f} L {mid[0]:.1f},{mid[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        else:
            # spline/auto — для простоты: квадратичная кривая
            cx = (p1[0] + p2[0]) / 2
            cy = (p1[1] + p2[1]) / 2
            d = f'M {p1[0]:.1f},{p1[1]:.1f} Q {cx:.1f},{cy:.1f} {p2[0]:.1f},{p2[1]:.1f}'

        parts.append(f'<path d="{d}" fill="none" stroke="{arrow_color}" stroke-width="{defs.style_arrow_thickness}"/>')

        # Стрелочная головка (две короткие линии)
        ang = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
        a1, a2 = ang - math.pi/7, ang + math.pi/7
        s = 6 * defs.style_arrow_size
        x1, y1 = p2[0] - s * math.cos(a1), p2[1] - s * math.sin(a1)
        x2, y2 = p2[0] - s * math.cos(a2), p2[1] - s * math.sin(a2)
        parts.append(f'<path d="M {p2[0]:.1f},{p2[1]:.1f} L {x1:.1f},{y1:.1f} M {p2[0]:.1f},{p2[1]:.1f} L {x2:.1f},{y2:.1f}" '
                     f'stroke="{arrow_color}" stroke-width="{max(1.0, defs.style_arrow_thickness-0.5)}"/>')

        # Подпись стрелки по offset (0..1) — линейно между p1 и p2
        if a.label:
            t = float(st["label_offset"])
            t = max(0.0, min(1.0, t))
            lx = p1[0] + (p2[0]-p1[0]) * t
            ly = p1[1] + (p2[1]-p1[1]) * t - 4
            font_style = "italic" if defs.font_italic_arrow else "normal"
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                f'font-family="{defs.font_family}" font-size="{defs.font_size_arrow}" '
                f'fill="{arrow_color}" font-style="{font_style}">{svg_escape(a.label)}</text>'
            )

    parts.append("</svg>")
    svg = "\n".join(parts)
    write_text(out_svg, svg)
    return svg


# ----------------------------
# Запись результатов в TOML
# ----------------------------

def write_positions_table(orig_path: Path, di: Diagram, rc: RunConfig) -> None:
    """
    Обновить/добавить секцию:
      [layout_result.blocks_pos]
      block_id = [x_norm, y_norm]
    Учитывается persist.write_mode и persist.sort_blocks.
    """
    text = read_text(orig_path)

    # Соберём пары (id, x, y) с привязкой к сетке
    pairs = []
    for b in di.blocks:
        x, y = b.pos if b.pos is not None else (0.5, 0.5)
        x = clamp01(round_to_grid(x, rc.layout.grid_snap))
        y = clamp01(round_to_grid(y, rc.layout.grid_snap))
        pairs.append((b.id, x, y))

    # Сортировка
    if rc.persist.sort_blocks == "by_id":
        pairs.sort(key=lambda t: t[0])
    else:
        pairs.sort(key=lambda t: (t[1], t[2], t[0]))

    # Разберём, была ли секция раньше
    sec_re = re.compile(r'(?ms)^\[layout_result\.blocks_pos\]\s*(.*?)\s*(?=^\[|\Z)')
    m = sec_re.search(text)
    existing = {}
    if m:
        body = m.group(1)
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            kv = line.split("=")
            if len(kv) >= 2:
                key = kv[0].strip()
                nums = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', kv[1])
                if len(nums) >= 2:
                    existing[key] = (float(nums[0]), float(nums[1]))

    # Сформируем новое тело секции
    lines = ["[layout_result.blocks_pos]"]
    if rc.persist.write_mode == "update_missing":
        # добавляем только те, которых не было
        for k, v in existing.items():
            lines.append(f'{k} = [{v[0]:.4f}, {v[1]:.4f}]')
        ex_keys = set(existing.keys())
        for bid, x, y in pairs:
            if bid not in ex_keys:
                lines.append(f'{bid} = [{x:.4f}, {y:.4f}]')
    else:
        # overwrite
        for bid, x, y in pairs:
            lines.append(f'{bid} = [{x:.4f}, {y:.4f}]')

    new_section = "\n".join(lines) + "\n"

    # Вставим/заменим в тексте
    if rc.persist.create_backup:
        make_backup(orig_path)

    if m:
        new_text = text[:m.start()] + new_section + text[m.end():]
    else:
        if not text.endswith("\n"):
            text += "\n"
        new_text = text + "\n" + new_section

    write_text(orig_path, new_text)
    print("INFO: positions written")


def write_geometry_into_blocks(orig_path: Path, di: Diagram, rc: RunConfig) -> None:
    """
    При необходимости записать прямо в [[blocks]]:
      pos = [x, y], width, header_height, prop_height
    Записываются только поля, перечисленные в persist.persist_geometry_fields.
    Если локального значения ширины/высоты не было, но хотим «зафиксировать» —
    можно перед вызовом проставить им глобальные значения (смотри вызов ниже).
    """
    if not rc.persist.write_block_geometry:
        return

    text = read_text(orig_path)
    lines = text.splitlines()
    out: List[str] = []
    i = 0

    # Быстрый доступ к блокам по id
    by_id: Dict[str, Block] = {b.id: b for b in di.blocks}
    want = set(rc.persist.persist_geometry_fields)

    def fmt(x: float) -> str:
        s = f"{x:.4f}"
        return s.rstrip("0").rstrip(".") if "." in s else s

    while i < len(lines):
        line = lines[i]
        out.append(line)

        if line.strip().startswith("[[blocks]]"):
            # Собираем текущую секцию [[blocks]] до следующего заголовка
            j = i + 1
            sect = [line]
            while j < len(lines) and not lines[j].strip().startswith("["):
                sect.append(lines[j]); j += 1

            sec_text = "\n".join(sect)
            m = re.search(r'^\s*id\s*=\s*"(.*?)"\s*$', sec_text, re.M)
            if m:
                bid = m.group(1)
                b = by_id.get(bid)
                if b:
                    # Убедимся, что у блока есть pos (уже после разводки)
                    pos = b.pos if b.pos is not None else (0.5, 0.5)
                    # Если хотим «зафиксировать» и размеры — гарантированно проставим им локальные значения:
                    # (Это упрощает жизнь: width/header_height/prop_height будут явно записаны в файл)
                    if "width" in want and b.width is None: b.width = rc.defaults.block_width
                    if "header_height" in want and b.header_height is None: b.header_height = rc.defaults.block_header_height
                    if "prop_height" in want and b.prop_height is None: b.prop_height = rc.defaults.block_prop_height

                    # Обновим/вставим строки
                    if "pos" in want:
                        if re.search(r'^\s*pos\s*=', sec_text, re.M):
                            sec_text = re.sub(r'^\s*pos\s*=.*$', f'pos = [{fmt(pos[0])}, {fmt(pos[1])}]', sec_text, flags=re.M)
                        else:
                            sec_text += f'\npos = [{fmt(pos[0])}, {fmt(pos[1])}]'

                    if "width" in want and b.width is not None:
                        if re.search(r'^\s*width\s*=', sec_text, re.M):
                            sec_text = re.sub(r'^\s*width\s*=.*$', f'width = {fmt(b.width)}', sec_text, flags=re.M)
                        else:
                            sec_text += f'\nwidth = {fmt(b.width)}'

                    if "header_height" in want and b.header_height is not None:
                        if re.search(r'^\s*header_height\s*=', sec_text, re.M):
                            sec_text = re.sub(r'^\s*header_height\s*=.*$', f'header_height = {fmt(b.header_height)}', sec_text, flags=re.M)
                        else:
                            sec_text += f'\nheader_height = {fmt(b.header_height)}'

                    if "prop_height" in want and b.prop_height is not None:
                        if re.search(r'^\s*prop_height\s*=', sec_text, re.M):
                            sec_text = re.sub(r'^\s*prop_height\s*=.*$', f'prop_height = {fmt(b.prop_height)}', sec_text, flags=re.M)
                        else:
                            sec_text += f'\nprop_height = {fmt(b.prop_height)}'

                    # Заменим секцию в выходе
                    sec_lines = sec_text.splitlines()
                    out[-1] = sec_lines[0]  # [[blocks]]
                    out.extend(sec_lines[1:])
                    i = j
                    continue
        i += 1

    new_text = "\n".join(out)
    if rc.persist.create_backup:
        make_backup(orig_path)
    write_text(orig_path, new_text)
    print("INFO: block geometry written")


# -------------
# Обход входа
# -------------
def discover_files(rc: RunConfig) -> List[Path]:
    """Вернуть список TOML-файлов по input_dirs с учётом recursive/include/exclude."""
    from fnmatch import fnmatch
    res: List[Path] = []
    for base in rc.input_dirs:
        base = Path(base)
        if not base.exists():
            continue
        it = base.rglob("*") if rc.recursive else base.glob("*")
        for p in it:
            if p.is_file() and p.suffix.lower().lstrip(".") in rc.include_extensions:
                rel = str(p).replace("\\", "/")
                if any(fnmatch(rel, pat) for pat in rc.exclude_patterns):
                    continue
                res.append(p)
    return res


# -------------
# Основной цикл
# -------------
def process_file(path: Path, rc: RunConfig) -> None:
    print(f"[..] {path}")
    di = parse_diagram(path)

    # 1) Раскладка (только pos, без знаний о пикселях/размерах)
    if rc.layout.mode == "layered":
        layered_layout(di, rc)
    elif rc.layout.mode == "force":
        # для простоты в этой версии оставим только layered/off;
        # при желании сюда можно вставить force-модель.
        layered_layout(di, rc)
    else:
        # off — ничего не делаем
        pass

    # 2) Пересчёт пикселей
    W, H = compute_pixel_geometry(di, rc.defaults)

    # 3) «Разводка» без наложений (учитывает реальные размеры)
    if rc.layout.avoid_node_overlap:
        resolve_overlaps_by_layers(di, rc, W, H)

    # 4) Сохранить SVG (+PNG при наличии cairosvg)
    out_svg = path.with_suffix(".svg")
    svg = render_svg(di, rc.defaults, out_svg)

    if rc.output.save_png and _HAS_CAIROSVG:
        out_png = path.with_suffix(".png")
        try:
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_png), dpi=rc.output.png_dpi)
        except Exception as e:
            print("WARN: не удалось экспортировать PNG через cairosvg:", e)

    # 5) Запись результатов обратно в файл
    if rc.persist.write_positions_to_input:
        write_positions_table(path, di, rc)

    # 6) При необходимости — зафиксировать геометрию в [[blocks]]
    if rc.persist.write_block_geometry:
        # Чтобы гарантированно появились width/header_height/prop_height — проставим их, если пусто:
        for b in di.blocks:
            if b.width is None: b.width = rc.defaults.block_width
            if b.header_height is None: b.header_height = rc.defaults.block_header_height
            if b.prop_height is None: b.prop_height = rc.defaults.block_prop_height
        write_geometry_into_blocks(path, di, rc)

    # 7) Открыть SVG в браузере (если включено)
    if rc.output.open_in_browser == "svg":
        try:
            import webbrowser
            webbrowser.open(str(out_svg))
        except Exception:
            pass

    print(f"OK: {path.name} → {out_svg.name}")


def main() -> None:
    here = Path(__file__).resolve().parent
    run_path = here / "run.toml"
    if not run_path.exists():
        print("ERROR: run.toml не найден рядом со скриптом.")
        sys.exit(2)

    rc = load_run_config(run_path)
    files = discover_files(rc)
    if not files:
        print("WARN: не найдено ни одного TOML-файла (проверьте input_dirs).")
        return

    for f in files:
        process_file(f, rc)

    print("Готово.")

if __name__ == "__main__":
    main()
