#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
draw_graph.py — простая и подробная версия
------------------------------------------
Формат данных: ТОЛЬКО [[blocks]] и [[blocks.outs]].
Глобальные [[arrows]] и списки 'outs = [...]' — автоматически мигрируются
в [[blocks.outs]] и удаляются из файла при записи.

Приоритет значений:
  1) Ручные (без префикса auto_): pos, width, header_height, prop_height,
     shape, corner_radius, stroke_width, fill/stroke, font.*, text_align_*, text_valign_*,
     text_padding_* и т.п.
  2) Авто (с префиксом auto_*): авто-значения, которые скрипт пишет сам
     на КАЖДОМ запуске (предварительно удаляя старые auto_* строки).
  3) Глобальные defaults из run.toml.

«Заморозка» авто-параметров:
  freeze_auto_pos/size/shape/fonts/style/text = true  → соответствующие auto_* НЕ перезаписываются.

Подписи стрелок по центру — style.label_offset = 0.5 (или auto_label_offset).

Направление слева-направо: [layout].direction="LR" (по умолчанию).
"""

from __future__ import annotations

import math
import re
import shutil
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- TOML: stdlib в Python 3.11+
try:
    import tomllib  # type: ignore
except Exception as e:
    print("ERROR: Нужен Python 3.11+ (модуль tomllib в стандартной библиотеке).", e)
    sys.exit(1)

# --- PNG экспорт (не обязателен)
_HAS_CAIROSVG = False
try:
    import cairosvg  # type: ignore
    _HAS_CAIROSVG = True
except Exception:
    pass


# =============== маленькие утилиты ===============

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def make_backup(src: Path) -> None:
    bak = src.with_suffix(src.suffix + ".bak")
    shutil.copy2(src, bak)

def round_to_grid(x: float, step: float) -> float:
    if step <= 0:
        return x
    return round(x / step) * step


# =============== конфиги ===============

@dataclass
class Defaults:
    # Холст
    canvas_size: Tuple[int, int] = (1200, 800)

    # Блок: нормированные размеры (0..1)
    block_width: float = 0.22
    block_header_height: float = 0.12
    block_prop_height: float = 0.06

    # Форма и стиль блока
    block_shape: str = "rounded"           # rect|rounded|pill|ellipse
    block_corner_radius: float = 10.0      # px
    block_stroke_width: float = 2.0        # px
    block_fill: str = "none"               # none|#RRGGBB|rgba(...)
    block_stroke: str = "#000000"

    # Шрифты
    font_family: str = "Arial"
    font_size_title: int = 14
    font_size_prop: int = 12
    font_bold_title: bool = True
    font_italic_arrow: bool = True

    # Текст в блоке — выравнивание и отступы
    text_align_title: str = "center"       # left|center|right
    text_align_props: str = "left"
    text_valign_title: str = "baseline"    # baseline|middle
    text_valign_props: str = "baseline"
    text_padding_title_x: float = 6        # px
    text_padding_title_y: float = 6
    text_padding_prop_x: float = 6
    text_padding_prop_y: float = 6

    # Тема (фон/цвета текста/стрелок по умолчанию)
    theme_background: str = "#FFFFFF"
    theme_text: str = "#000000"
    theme_arrow: str = "#222222"

    # Стрелки: общие стили (могут переопределяться локально)
    style_curve: str = "auto"              # auto|straight|orthogonal|spline
    style_label_offset: float = 0.5        # 0..1
    style_connector_from: str = "auto"     # auto|left|right|top|bottom
    style_connector_to: str = "auto"
    style_arrow_size: float = 1.0          # множитель размера наконечника
    style_arrow_thickness: float = 2.0     # px


@dataclass
class LayoutCfg:
    mode: str = "layered"                  # layered|off
    direction: str = "LR"                  # LR|RL|TB|BT
    minimize_edge_crossings: bool = True
    avoid_node_overlap: bool = True
    node_gap: float = 0.03                 # нормированный зазор во «внутрислоевой» оси
    layer_gap: float = 0.08                # нормированный зазор по главной оси слоёв
    respect_fixed_blocks: bool = True
    grid_snap: float = 0.01                # привязка pos/auto_pos при записи
    deterministic: bool = True
    seed: int = 42


@dataclass
class PersistCfg:
    create_backup: bool = True
    # какие группы auto_* писать (и нести ответственность):
    persist_auto_fields: List[str] = field(default_factory=lambda: [
        "pos", "size", "shape", "fonts", "style", "text"
    ])
    # заморозка групп (не перезаписывать соответствующие auto_*)
    freeze_auto_pos: bool = False
    freeze_auto_size: bool = False
    freeze_auto_shape: bool = False
    freeze_auto_fonts: bool = False
    freeze_auto_style: bool = False
    freeze_auto_text: bool = False


@dataclass
class OutputCfg:
    save_svg: bool = True
    save_png: bool = True
    png_dpi: int = 200
    open_in_browser: str = "svg"           # none|svg


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


# =============== модель графа ===============

@dataclass
class Block:
    id: str
    title: str
    properties: List[str]

    # --- РУЧНЫЕ (фиксируемые пользователем) ---
    pos: Optional[Tuple[float, float]] = None
    width: Optional[float] = None
    header_height: Optional[float] = None
    prop_height: Optional[float] = None

    shape: Optional[str] = None               # rect|rounded|pill|ellipse
    corner_radius: Optional[float] = None     # px
    stroke_width: Optional[float] = None      # px
    fill: Optional[str] = None
    stroke: Optional[str] = None

    font_family: Optional[str] = None
    font_size_title: Optional[int] = None
    font_size_prop: Optional[int] = None
    font_bold_title: Optional[bool] = None
    font_italic_arrow: Optional[bool] = None

    text_align_title: Optional[str] = None    # left|center|right
    text_align_props: Optional[str] = None
    text_valign_title: Optional[str] = None   # baseline|middle
    text_valign_props: Optional[str] = None
    text_padding_title_x: Optional[float] = None
    text_padding_title_y: Optional[float] = None
    text_padding_prop_x: Optional[float] = None
    text_padding_prop_y: Optional[float] = None

    # --- АВТО (пересчитываются каждый запуск) ---
    auto_pos: Optional[Tuple[float, float]] = None
    auto_width: Optional[float] = None
    auto_header_height: Optional[float] = None
    auto_prop_height: Optional[float] = None

    auto_shape: Optional[str] = None
    auto_corner_radius: Optional[float] = None
    auto_stroke_width: Optional[float] = None
    auto_fill: Optional[str] = None
    auto_stroke: Optional[str] = None

    auto_font_family: Optional[str] = None
    auto_font_size_title: Optional[int] = None
    auto_font_size_prop: Optional[int] = None
    auto_font_bold_title: Optional[bool] = None
    auto_font_italic_arrow: Optional[bool] = None

    auto_text_align_title: Optional[str] = None
    auto_text_align_props: Optional[str] = None
    auto_text_valign_title: Optional[str] = None
    auto_text_valign_props: Optional[str] = None
    auto_text_padding_title_x: Optional[float] = None
    auto_text_padding_title_y: Optional[float] = None
    auto_text_padding_prop_x: Optional[float] = None
    auto_text_padding_prop_y: Optional[float] = None

    # --- флаги заморозки (локальные, если захочешь) ---
    freeze_auto_pos: Optional[bool] = None
    freeze_auto_size: Optional[bool] = None
    freeze_auto_shape: Optional[bool] = None
    freeze_auto_fonts: Optional[bool] = None
    freeze_auto_style: Optional[bool] = None
    freeze_auto_text: Optional[bool] = None

    # --- вычисляемые пиксели (внутренне) ---
    w_px: float = 0.0
    h_px: float = 0.0
    cx_px: float = 0.0
    cy_px: float = 0.0

    # --- утилиты «эффективных» значений (ручное > авто > дефолт) ---
    def eff_pos(self) -> Optional[Tuple[float, float]]:
        return self.pos if self.pos is not None else self.auto_pos
    def eff_width(self, d: Defaults) -> float:
        return self.width if self.width is not None else (self.auto_width if self.auto_width is not None else d.block_width)
    def eff_header(self, d: Defaults) -> float:
        return self.header_height if self.header_height is not None else (self.auto_header_height if self.auto_header_height is not None else d.block_header_height)
    def eff_prop(self, d: Defaults) -> float:
        return self.prop_height if self.prop_height is not None else (self.auto_prop_height if self.auto_prop_height is not None else d.block_prop_height)

    def eff_shape(self, d: Defaults) -> str:
        return self.shape or self.auto_shape or d.block_shape
    def eff_corner_radius(self, d: Defaults) -> float:
        return (self.corner_radius if self.corner_radius is not None else
                (self.auto_corner_radius if self.auto_corner_radius is not None else d.block_corner_radius))
    def eff_stroke_width(self, d: Defaults) -> float:
        return (self.stroke_width if self.stroke_width is not None else
                (self.auto_stroke_width if self.auto_stroke_width is not None else d.block_stroke_width))
    def eff_fill(self, d: Defaults) -> str:
        return self.fill or self.auto_fill or d.block_fill
    def eff_stroke(self, d: Defaults) -> str:
        return self.stroke or self.auto_stroke or d.block_stroke

    def eff_font_family(self, d: Defaults) -> str:
        return self.font_family or self.auto_font_family or d.font_family
    def eff_font_size_title(self, d: Defaults) -> int:
        return self.font_size_title if self.font_size_title is not None else (self.auto_font_size_title if self.auto_font_size_title is not None else d.font_size_title)
    def eff_font_size_prop(self, d: Defaults) -> int:
        return self.font_size_prop if self.font_size_prop is not None else (self.auto_font_size_prop if self.auto_font_size_prop is not None else d.font_size_prop)
    def eff_font_bold_title(self, d: Defaults) -> bool:
        v = self.font_bold_title if self.font_bold_title is not None else (self.auto_font_bold_title if self.auto_font_bold_title is not None else d.font_bold_title)
        return bool(v)
    def eff_font_italic_arrow(self, d: Defaults) -> bool:
        v = self.font_italic_arrow if self.font_italic_arrow is not None else (self.auto_font_italic_arrow if self.auto_font_italic_arrow is not None else d.font_italic_arrow)
        return bool(v)

    def eff_text_align_title(self, d: Defaults) -> str:
        return self.text_align_title or self.auto_text_align_title or d.text_align_title
    def eff_text_align_props(self, d: Defaults) -> str:
        return self.text_align_props or self.auto_text_align_props or d.text_align_props
    def eff_text_valign_title(self, d: Defaults) -> str:
        return self.text_valign_title or self.auto_text_valign_title or d.text_valign_title
    def eff_text_valign_props(self, d: Defaults) -> str:
        return self.text_valign_props or self.auto_text_valign_props or d.text_valign_props

    def eff_text_pad_title_x(self, d: Defaults) -> float:
        return self.text_padding_title_x if self.text_padding_title_x is not None else (self.auto_text_padding_title_x if self.auto_text_padding_title_x is not None else d.text_padding_title_x)
    def eff_text_pad_title_y(self, d: Defaults) -> float:
        return self.text_padding_title_y if self.text_padding_title_y is not None else (self.auto_text_padding_title_y if self.auto_text_padding_title_y is not None else d.text_padding_title_y)
    def eff_text_pad_prop_x(self, d: Defaults) -> float:
        return self.text_padding_prop_x if self.text_padding_prop_x is not None else (self.auto_text_padding_prop_x if self.auto_text_padding_prop_x is not None else d.text_padding_prop_x)
    def eff_text_pad_prop_y(self, d: Defaults) -> float:
        return self.text_padding_prop_y if self.text_padding_prop_y is not None else (self.auto_text_padding_prop_y if self.auto_text_padding_prop_y is not None else d.text_padding_prop_y)


@dataclass
class Arrow:
    # Источник определяется блоком-родителем (где лежит [[blocks.outs]])
    from_id: str
    to_id: str
    label: Optional[str] = None

    # Локальные РУЧНЫЕ стили
    style_curve: Optional[str] = None            # straight|orthogonal|spline|auto
    style_label_offset: Optional[float] = None   # 0..1
    style_connector_from: Optional[str] = None   # auto|left|right|top|bottom
    style_connector_to: Optional[str] = None

    # Локальные АВТО стили (пересчитываются)
    auto_curve: Optional[str] = None
    auto_label_offset: Optional[float] = None
    auto_connector_from: Optional[str] = None
    auto_connector_to: Optional[str] = None

    # Эффективное значение стиля (ручное > авто > defaults)
    def eff(self, d: Defaults) -> Dict[str, object]:
        return {
            "curve": self.style_curve or self.auto_curve or d.style_curve,
            "label_offset": (
                self.style_label_offset
                if self.style_label_offset is not None
                else (self.auto_label_offset if self.auto_label_offset is not None else d.style_label_offset)
            ),
            "connector_from": self.style_connector_from or self.auto_connector_from or d.style_connector_from,
            "connector_to": self.style_connector_to or self.auto_connector_to or d.style_connector_to,
        }


@dataclass
class Diagram:
    meta: Dict[str, object]
    blocks: List[Block]
    arrows: List[Arrow]


# =============== загрузка run.toml ===============

def load_run_config(path: Path) -> RunConfig:
    cfg = tomllib.loads(read_text(path))
    def get(d, k, default=None):
        return d.get(k, default) if isinstance(d, dict) else default

    rc = RunConfig()
    rc.input_dirs = cfg.get("input_dirs", [])
    rc.recursive = cfg.get("recursive", True)
    rc.include_extensions = cfg.get("include_extensions", ["toml"])
    rc.exclude_patterns = cfg.get("exclude_patterns", [])

    # layout
    L = cfg.get("layout", {})
    rc.layout = LayoutCfg(
        mode=get(L, "mode", "layered"),
        direction=get(L, "direction", "LR"),
        minimize_edge_crossings=get(L, "minimize_edge_crossings", True),
        avoid_node_overlap=get(L, "avoid_node_overlap", True),
        node_gap=float(get(L, "node_gap", 0.03)),
        layer_gap=float(get(L, "layer_gap", 0.08)),
        respect_fixed_blocks=get(L, "respect_fixed_blocks", True),
        grid_snap=float(get(L, "grid_snap", 0.01)),
        deterministic=get(L, "deterministic", True),
        seed=int(get(L, "seed", 42)),
    )

    # persist
    P = cfg.get("persist", {})
    rc.persist = PersistCfg(
        create_backup=get(P, "create_backup", True),
        persist_auto_fields=get(P, "persist_auto_fields", ["pos","size","shape","fonts","style","text"]),
        freeze_auto_pos=get(P, "freeze_auto_pos", False),
        freeze_auto_size=get(P, "freeze_auto_size", False),
        freeze_auto_shape=get(P, "freeze_auto_shape", False),
        freeze_auto_fonts=get(P, "freeze_auto_fonts", False),
        freeze_auto_style=get(P, "freeze_auto_style", False),
        freeze_auto_text=get(P, "freeze_auto_text", False),
    )

    # output
    O = cfg.get("output", {})
    rc.output = OutputCfg(
        save_svg=get(O, "save_svg", True),
        save_png=get(O, "save_png", True),
        png_dpi=int(get(O, "png_dpi", 200)),
        open_in_browser=get(O, "open_in_browser", "svg"),
    )

    # defaults
    D = cfg.get("defaults", {})
    rc.defaults = Defaults(
        canvas_size=tuple(get(D, "canvas_size", [1200, 800])),
        block_width=float(get(D, "block.width", 0.22)),
        block_header_height=float(get(D, "block.header_height", 0.12)),
        block_prop_height=float(get(D, "block.prop_height", 0.06)),
        block_shape=get(D, "block.shape", "rounded"),
        block_corner_radius=float(get(D, "block.corner_radius", 10.0)),
        block_stroke_width=float(get(D, "block.stroke_width", 2.0)),
        block_fill=get(D, "block.fill_color", "none"),
        block_stroke=get(D, "block.stroke_color", "#000000"),
        font_family=get(D, "font.family", "Arial"),
        font_size_title=int(get(D, "font.size_title", 14)),
        font_size_prop=int(get(D, "font.size_prop", 12)),
        font_bold_title=bool(get(D, "font.bold_title", True)),
        font_italic_arrow=bool(get(D, "font.italic_arrow", True)),
        text_align_title=get(D, "block.text_align_title", "center"),
        text_align_props=get(D, "block.text_align_props", "left"),
        text_valign_title=get(D, "block.text_valign_title", "baseline"),
        text_valign_props=get(D, "block.text_valign_props", "baseline"),
        text_padding_title_x=float(get(D, "block.text_padding_title_x", 6)),
        text_padding_title_y=float(get(D, "block.text_padding_title_y", 6)),
        text_padding_prop_x=float(get(D, "block.text_padding_prop_x", 6)),
        text_padding_prop_y=float(get(D, "block.text_padding_prop_y", 6)),
        theme_background=get(D, "theme.background", "#FFFFFF"),
        theme_text=get(D, "theme.text_color", "#000000"),
        theme_arrow=get(D, "theme.arrow_color", "#222222"),
        style_curve=get(D, "style.curve", "auto"),
        style_label_offset=float(get(D, "style.label_offset", 0.5)),
        style_connector_from=get(D, "style.connector_from", "auto"),
        style_connector_to=get(D, "style.connector_to", "auto"),
        style_arrow_size=float(get(D, "style.arrow_size", 1.0)),
        style_arrow_thickness=float(get(D, "style.arrow_thickness", 2.0)),
    )
    return rc


# =============== парсинг TOML графа + миграция в памяти ===============

def parse_diagram(path: Path) -> Diagram:
    data = tomllib.loads(read_text(path))
    meta = data.get("meta", {}) or {}

    # Блоки
    blocks_raw = data.get("blocks", []) or []
    blocks: List[Block] = []
    seen = set()

    for b in blocks_raw:
        bid = b.get("id")
        if not bid or bid in seen:
            raise ValueError(f"Пустой/дублирующийся id блока в {path}")
        seen.add(bid)

        def tup2(v):
            return (float(v[0]), float(v[1])) if isinstance(v, list) and len(v) == 2 else None

        blocks.append(Block(
            id=bid,
            title=b.get("title", ""),
            properties=list(b.get("properties", [])),

            # Ручные
            pos=tup2(b.get("pos")),
            width=b.get("width"),
            header_height=b.get("header_height"),
            prop_height=b.get("prop_height"),
            shape=b.get("shape"),
            corner_radius=b.get("corner_radius"),
            stroke_width=b.get("stroke_width"),
            fill=b.get("fill"),
            stroke=b.get("stroke"),
            font_family=b.get("font.family"),
            font_size_title=b.get("font.size_title"),
            font_size_prop=b.get("font.size_prop"),
            font_bold_title=b.get("font.bold_title"),
            font_italic_arrow=b.get("font.italic_arrow"),
            text_align_title=b.get("text_align_title"),
            text_align_props=b.get("text_align_props"),
            text_valign_title=b.get("text_valign_title"),
            text_valign_props=b.get("text_valign_props"),
            text_padding_title_x=b.get("text_padding_title_x"),
            text_padding_title_y=b.get("text_padding_title_y"),
            text_padding_prop_x=b.get("text_padding_prop_x"),
            text_padding_prop_y=b.get("text_padding_prop_y"),

            # Авто
            auto_pos=tup2(b.get("auto_pos")),
            auto_width=b.get("auto_width"),
            auto_header_height=b.get("auto_header_height"),
            auto_prop_height=b.get("auto_prop_height"),
            auto_shape=b.get("auto_shape"),
            auto_corner_radius=b.get("auto_corner_radius"),
            auto_stroke_width=b.get("auto_stroke_width"),
            auto_fill=b.get("auto_fill"),
            auto_stroke=b.get("auto_stroke"),
            auto_font_family=b.get("auto_font_family"),
            auto_font_size_title=b.get("auto_font_size_title"),
            auto_font_size_prop=b.get("auto_font_size_prop"),
            auto_font_bold_title=b.get("auto_font_bold_title"),
            auto_font_italic_arrow=b.get("auto_font_italic_arrow"),
            auto_text_align_title=b.get("auto_text_align_title"),
            auto_text_align_props=b.get("auto_text_align_props"),
            auto_text_valign_title=b.get("auto_text_valign_title"),
            auto_text_valign_props=b.get("auto_text_valign_props"),
            auto_text_padding_title_x=b.get("auto_text_padding_title_x"),
            auto_text_padding_title_y=b.get("auto_text_padding_title_y"),
            auto_text_padding_prop_x=b.get("auto_text_padding_prop_x"),
            auto_text_padding_prop_y=b.get("auto_text_padding_prop_y"),

            # локальные заморозки (опционально)
            freeze_auto_pos=b.get("freeze_auto_pos"),
            freeze_auto_size=b.get("freeze_auto_size"),
            freeze_auto_shape=b.get("freeze_auto_shape"),
            freeze_auto_fonts=b.get("freeze_auto_fonts"),
            freeze_auto_style=b.get("freeze_auto_style"),
            freeze_auto_text=b.get("freeze_auto_text"),
        ))

    # Стрелки: собираем ТОЛЬКО из [[blocks.outs]] и (временно) из глобальных [[arrows]]
    arrows: List[Arrow] = []

    # (1) Вложенные outs у каждого блока
    for b_raw in blocks_raw:
        frm = b_raw.get("id")
        outs_raw = b_raw.get("outs")  # может быть список строк ИЛИ список объектов (после миграции)
        # вариант до миграции: outs = ["B","C"]
        if isinstance(outs_raw, list) and outs_raw and isinstance(outs_raw[0], str):
            for to in outs_raw:
                arrows.append(Arrow(from_id=frm, to_id=to))
        # вариант после миграции: [[blocks.outs]] как список таблиц
        if isinstance(outs_raw, list) and outs_raw and isinstance(outs_raw[0], dict):
            for o in outs_raw:
                to = o.get("to")
                if not to:
                    continue
                ar = Arrow(
                    from_id=frm, to_id=to, label=o.get("label"),
                    style_curve=o.get("style.curve"),
                    style_label_offset=o.get("style.label_offset"),
                    style_connector_from=o.get("style.connector_from"),
                    style_connector_to=o.get("style.connector_to"),
                    auto_curve=o.get("auto_curve"),
                    auto_label_offset=o.get("auto_label_offset"),
                    auto_connector_from=o.get("auto_connector_from"),
                    auto_connector_to=o.get("auto_connector_to"),
                )
                arrows.append(ar)

    # (2) Глобальные [[arrows]] (для обратной совместимости — позже перепишем их в blocks.outs)
    for a in data.get("arrows", []) or []:
        frm, to = a.get("from"), a.get("to")
        if not frm or not to:
            continue
        ar = Arrow(
            from_id=frm, to_id=to, label=a.get("label"),
            style_curve=a.get("style.curve"),
            style_label_offset=a.get("style.label_offset"),
            style_connector_from=a.get("style.connector_from"),
            style_connector_to=a.get("style.connector_to"),
            auto_curve=a.get("auto_curve"),
            auto_label_offset=a.get("auto_label_offset"),
            auto_connector_from=a.get("auto_connector_from"),
            auto_connector_to=a.get("auto_connector_to"),
        )
        arrows.append(ar)

    return Diagram(meta=meta, blocks=blocks, arrows=arrows)


# =============== раскладка (layered) ===============

def layered_layout(di: Diagram, rc: RunConfig) -> None:
    """
    Ставит стартовые auto_pos ТОЛЬКО тем, у кого нет ручного pos.
    (Если уже есть auto_pos — можно оставить как есть, всё равно перезапишем позже.)
    """
    direction = (rc.layout.direction or "LR").upper()
    LR = direction in ("LR", "RL")
    reverse_main = direction in ("RL", "BT")

    incoming: Dict[str, List[str]] = {b.id: [] for b in di.blocks}
    outgoing: Dict[str, List[str]] = {b.id: [] for b in di.blocks}
    ids = {b.id for b in di.blocks}
    for a in di.arrows:
        if a.from_id in ids and a.to_id in ids:
            outgoing[a.from_id].append(a.to_id)
            incoming[a.to_id].append(a.from_id)

    sources = [k for k, v in incoming.items() if not v] or ([di.blocks[0].id] if di.blocks else [])
    layer_of = {bid: math.inf for bid in ids}
    for s in sources:
        layer_of[s] = 0

    fr = list(sources)
    while fr:
        nf = []
        for u in fr:
            for v in outgoing.get(u, []):
                if layer_of[v] > layer_of[u] + 1:
                    layer_of[v] = layer_of[u] + 1
                    nf.append(v)
        fr = nf
    max_layer = max([0] + [d for d in layer_of.values() if d < math.inf])
    for bid, lv in list(layer_of.items()):
        if lv == math.inf:
            max_layer += 1
            layer_of[bid] = max_layer

    layers: Dict[int, List[str]] = {}
    for bid, lv in layer_of.items():
        layers.setdefault(int(lv), []).append(bid)

    order = sorted(layers.keys())
    if reverse_main:
        order = list(reversed(order))

    # простая упорядочивающая эвристика: учитывать соседей слева
    for i, L in enumerate(order):
        row = layers[L]
        if i > 0:
            left_ids = layers[order[i - 1]]
            pos_index = {bid: j for j, bid in enumerate(left_ids)}
            row.sort(key=lambda b: sum(pos_index.get(p, 0) for p in incoming.get(b, [])) / max(1, len(incoming.get(b, []))))
        layers[L] = row

    S = len(order)
    for si, L in enumerate(order):
        main_t = 0.1 + 0.8 * (si / max(1, S - 1)) if S > 1 else 0.5
        row = layers[L]; m = len(row)
        for j, bid in enumerate(row):
            b = next(bb for bb in di.blocks if bb.id == bid)
            if b.pos is not None and rc.layout.respect_fixed_blocks:
                continue
            if b.auto_pos is None:
                perp = 0.2 + 0.6 * (j / max(1, m - 1)) if m > 1 else 0.5
                x, y = (main_t, perp) if LR else (perp, main_t)
                if reverse_main:
                    if LR: x = 1.0 - x
                    else:  y = 1.0 - y
                b.auto_pos = (clamp01(x), clamp01(y))


# =============== пиксельная геометрия ===============

def compute_px(di: Diagram, d: Defaults) -> Tuple[int, int]:
    W, H = d.canvas_size
    cs = di.meta.get("canvas_size")
    if isinstance(cs, list) and len(cs) == 2:
        W, H = int(cs[0]), int(cs[1])
    for b in di.blocks:
        w = b.eff_width(d)
        hh = b.eff_header(d)
        ph = b.eff_prop(d)
        total_h = hh + ph * max(0, len(b.properties))
        px_pos = b.eff_pos() or (0.5, 0.5)
        b.w_px = max(1.0, w * W)
        b.h_px = max(1.0, total_h * H)
        b.cx_px = px_pos[0] * W
        b.cy_px = px_pos[1] * H
    return W, H


# =============== разводка без наложений ===============

def resolve_overlaps(di: Diagram, rc: RunConfig, W: int, H: int) -> None:
    LR = (rc.layout.direction or "LR").upper() in ("LR", "RL")
    blocks = list(di.blocks)
    blocks.sort(key=(lambda b: b.cx_px) if LR else (lambda b: b.cy_px))
    layer_thresh_px = (rc.layout.layer_gap if rc.layout.layer_gap > 0 else 0.08) * (W if LR else H)

    # группируем в слои по главной оси
    layers: List[List[Block]] = []
    cur: List[Block] = []
    last = None
    for b in blocks:
        m = b.cx_px if LR else b.cy_px
        if last is None or abs(m - last) <= layer_thresh_px:
            cur.append(b); last = m if last is None else (last + m) / 2
        else:
            layers.append(cur); cur = [b]; last = m
    if cur: layers.append(cur)

    gap_px = (rc.layout.node_gap if rc.layout.node_gap > 0 else 0.03) * (H if LR else W)

    # разводка «лесенкой» внутри слоя
    if LR:
        for row in layers:
            row.sort(key=lambda b: b.cy_px)
            top, bot = 0.10 * H, 0.90 * H
            for i, b in enumerate(row):
                if i == 0:
                    b.cy_px = max(top + b.h_px / 2, min(b.cy_px, bot - b.h_px / 2))
                else:
                    pr = row[i - 1]
                    miny = pr.cy_px + pr.h_px / 2 + gap_px + b.h_px / 2
                    b.cy_px = max(b.cy_px, miny)
                    if b.cy_px + b.h_px / 2 > bot:
                        b.cy_px = bot - b.h_px / 2
            for i in range(len(row) - 2, -1, -1):
                cb = row[i]; nx = row[i + 1]
                maxy = nx.cy_px - nx.h_px / 2 - gap_px - cb.h_px / 2
                cb.cy_px = min(cb.cy_px, maxy)
                if cb.cy_px - cb.h_px / 2 < top:
                    cb.cy_px = top + cb.h_px / 2
    else:
        for row in layers:
            row.sort(key=lambda b: b.cx_px)
            left, right = 0.10 * W, 0.90 * W
            for i, b in enumerate(row):
                if i == 0:
                    b.cx_px = max(left + b.w_px / 2, min(b.cx_px, right - b.w_px / 2))
                else:
                    pr = row[i - 1]
                    minx = pr.cx_px + pr.w_px / 2 + gap_px + b.w_px / 2
                    b.cx_px = max(b.cx_px, minx)
                    if b.cx_px + b.w_px / 2 > right:
                        b.cx_px = right - b.w_px / 2
            for i in range(len(row) - 2, -1, -1):
                cb = row[i]; nx = row[i + 1]
                maxx = nx.cx_px - nx.w_px / 2 - gap_px - cb.w_px / 2
                cb.cx_px = min(cb.cx_px, maxx)
                if cb.cx_px - cb.w_px / 2 < left:
                    cb.cx_px = left + cb.w_px / 2

    # страховка от выхода за край
    pad = 0.02
    minx, maxx = pad * W, (1.0 - pad) * W
    miny, maxy = pad * H, (1.0 - pad) * H
    for b in di.blocks:
        b.cx_px = max(minx + b.w_px / 2, min(b.cx_px, maxx - b.w_px / 2))
        b.cy_px = max(miny + b.h_px / 2, min(b.cy_px, maxy - b.h_px / 2))

    # назад в auto_pos (только если нет ручного pos)
    for b in di.blocks:
        if b.pos is None:
            b.auto_pos = (clamp01(b.cx_px / W), clamp01(b.cy_px / H))


# =============== отрисовка SVG ===============

def svg_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def block_xywh(b: Block) -> Tuple[float, float, float, float]:
    x = b.cx_px - b.w_px / 2
    y = b.cy_px - b.h_px / 2
    return x, y, b.w_px, b.h_px

def render_svg(di: Diagram, d: Defaults, out_svg: Path) -> str:
    W, H = d.canvas_size
    cs = di.meta.get("canvas_size")
    if isinstance(cs, list) and len(cs) == 2:
        W, H = int(cs[0]), int(cs[1])

    bg = d.theme_background
    text_col = d.theme_text
    arrow_col = d.theme_arrow

    parts: List[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>')

    title = str(di.meta.get("title") or "")
    if title:
        parts.append(
            f'<text x="{W/2:.1f}" y="24" text-anchor="middle" '
            f'font-family="{d.font_family}" font-size="{d.font_size_title+2}" '
            f'fill="{text_col}" font-weight="bold">{svg_escape(title)}</text>'
        )

    # --- Блоки ---
    for b in di.blocks:
        x, y, w, h = block_xywh(b)

        # форма + рамка/заливка
        shape = (b.eff_shape(d) or "rect").lower()
        rr = b.eff_corner_radius(d)
        stroke_w = b.eff_stroke_width(d)
        fill = b.eff_fill(d)
        stroke = b.eff_stroke(d)

        if shape in ("rect", "rounded", "pill"):
            rx = ry = rr if shape != "rect" else 0
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" rx="{rx}" ry="{ry}" width="{w:.1f}" height="{h:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
            )
        elif shape == "ellipse":
            parts.append(
                f'<ellipse cx="{b.cx_px:.1f}" cy="{b.cy_px:.1f}" rx="{w/2:.1f}" ry="{h/2:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
            )
        else:
            # по умолчанию — прямоугольник
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_w}"/>'
            )

        # линия под шапкой
        HH = b.eff_header(d) * H
        parts.append(
            f'<line x1="{x:.1f}" y1="{y+HH:.1f}" x2="{x+w:.1f}" y2="{y+HH:.1f}" '
            f'stroke="{stroke}" stroke-width="{max(1.0, stroke_w/2)}"/>'
        )

        # --- Заголовок ---
        fw = "bold" if b.eff_font_bold_title(d) else "normal"
        ffam = b.eff_font_family(d)
        fsize_t = b.eff_font_size_title(d)
        # выравнивание
        ta = (b.eff_text_align_title(d) or "center").lower()   # left|center|right
        tanchor = "start" if ta == "left" else ("end" if ta == "right" else "middle")
        dax = b.eff_text_pad_title_x(d)
        day = b.eff_text_pad_title_y(d)
        if tanchor == "start":
            tx = x + dax
        elif tanchor == "end":
            tx = x + w - dax
        else:
            tx = x + w / 2

        # вертикальная привязка
        tv = (b.eff_text_valign_title(d) or "baseline").lower()  # baseline|middle
        if tv == "middle":
            ty = y + HH / 2
            dom = ' dominant-baseline="middle"'
        else:
            ty = y + HH - day
            dom = ''

        parts.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{tanchor}"{dom} '
            f'font-family="{ffam}" font-size="{fsize_t}" '
            f'fill="{text_col}" font-weight="{fw}">{svg_escape(b.title)}</text>'
        )

        # --- Свойства (подстроки) ---
        fsize_p = b.eff_font_size_prop(d)
        ta2 = (b.eff_text_align_props(d) or "left").lower()
        tanchor2 = "start" if ta2 == "left" else ("end" if ta2 == "right" else "middle")
        pax = b.eff_text_pad_prop_x(d)
        pay = b.eff_text_pad_prop_y(d)
        if tanchor2 == "start":
            px = x + pax
        elif tanchor2 == "end":
            px = x + w - pax
        else:
            px = x + w / 2

        tv2 = (b.eff_text_valign_props(d) or "baseline").lower()
        dom2 = ' dominant-baseline="middle"' if tv2 == "middle" else ''

        PH = b.eff_prop(d) * H
        for i, prop in enumerate(b.properties):
            # базовая линия строки:
            if tv2 == "middle":
                py = y + HH + PH * i + PH / 2
            else:
                py = y + HH + PH * (i + 1) - pay

            # разделительная линия (верх строки)
            parts.append(
                f'<line x1="{x:.1f}" y1="{y + HH + PH * i:.1f}" '
                f'x2="{x+w:.1f}" y2="{y + HH + PH * i:.1f}" '
                f'stroke="{stroke}" stroke-width="{max(0.5, stroke_w/2.5)}"/>'
            )
            parts.append(
                f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{tanchor2}"{dom2} '
                f'font-family="{ffam}" font-size="{fsize_p}" fill="{text_col}">{svg_escape(prop)}</text>'
            )

    # --- Стрелки ---
    id2b = {b.id: b for b in di.blocks}

    def conn_pt(bl: Block, side: str) -> Tuple[float, float]:
        x, y, w, h = block_xywh(bl)
        if side == "left":   return (x, y + h / 2)
        if side == "right":  return (x + w, y + h / 2)
        if side == "top":    return (x + w / 2, y)
        if side == "bottom": return (x + w / 2, y + h)
        return (bl.cx_px, bl.cy_px)

    def choose_side(p1, p2, pref: str) -> str:
        if pref != "auto": return pref
        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        if abs(dx) >= abs(dy):
            return "right" if dx >= 0 else "left"
        else:
            return "bottom" if dy >= 0 else "top"

    for a in di.arrows:
        if a.from_id not in id2b or a.to_id not in id2b:
            continue
        b1, b2 = id2b[a.from_id], id2b[a.to_id]
        st = a.eff(d)

        s1 = choose_side((b1.cx_px, b1.cy_px), (b2.cx_px, b2.cy_px), str(st["connector_from"]))
        s2 = choose_side((b2.cx_px, b2.cy_px), (b1.cx_px, b1.cy_px), str(st["connector_to"]))
        p1 = conn_pt(b1, s1); p2 = conn_pt(b2, s2)

        curve = str(st["curve"])
        if curve == "straight":
            d_path = f'M {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        elif curve == "orthogonal":
            mid = (p2[0], p1[1]) if abs(p2[0] - p1[0]) > abs(p2[1] - p1[1]) else (p1[0], p2[1])
            d_path = f'M {p1[0]:.1f},{p1[1]:.1f} L {mid[0]:.1f},{mid[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        else:
            cx = (p1[0] + p2[0]) / 2; cy = (p1[1] + p2[1]) / 2
            d_path = f'M {p1[0]:.1f},{p1[1]:.1f} Q {cx:.1f},{cy:.1f} {p2[0]:.1f},{p2[1]:.1f}'
        parts.append(f'<path d="{d_path}" fill="none" stroke="{arrow_col}" stroke-width="{d.style_arrow_thickness}"/>')

        # наконечник
        ang = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        a1, a2 = ang - math.pi / 7, ang + math.pi / 7
        s = 6 * d.style_arrow_size
        x1, y1 = p2[0] - s * math.cos(a1), p2[1] - s * math.sin(a1)
        x2, y2 = p2[0] - s * math.cos(a2), p2[1] - s * math.sin(a2)
        parts.append(
            f'<path d="M {p2[0]:.1f},{p2[1]:.1f} L {x1:.1f},{y1:.1f} M {p2[0]:.1f},{p2[1]:.1f} L {x2:.1f},{y2:.1f}" '
            f'stroke="{arrow_col}" stroke-width="{max(1.0, d.style_arrow_thickness - 0.5)}"/>'
        )

        # подпись
        if a.label:
            t = float(st["label_offset"])
            t = max(0.0, min(1.0, t))
            lx = p1[0] + (p2[0] - p1[0]) * t
            ly = p1[1] + (p2[1] - p1[1]) * t - 4
            font_style = "italic" if d.font_italic_arrow else "normal"
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
                f'font-family="{d.font_family}" font-size="{d.font_size_prop}" '
                f'fill="{arrow_col}" font-style="{font_style}">{svg_escape(a.label)}</text>'
            )

    parts.append("</svg>")
    svg = "\n".join(parts)
    write_text(out_svg, svg)
    return svg


# =============== запись: auto_* + миграция TOML на диске ===============

AUTO_KEYS_BLOCK = [
    # pos/size
    "auto_pos", "auto_width", "auto_header_height", "auto_prop_height",
    # shape/style
    "auto_shape", "auto_corner_radius", "auto_stroke_width", "auto_fill", "auto_stroke",
    # fonts
    "auto_font_family", "auto_font_size_title", "auto_font_size_prop", "auto_font_bold_title", "auto_font_italic_arrow",
    # text (align/valign/padding)
    "auto_text_align_title", "auto_text_align_props",
    "auto_text_valign_title", "auto_text_valign_props",
    "auto_text_padding_title_x", "auto_text_padding_title_y",
    "auto_text_padding_prop_x", "auto_text_padding_prop_y",
]

AUTO_KEYS_OUT = [
    "auto_curve", "auto_label_offset", "auto_connector_from", "auto_connector_to"
]

def _fmt(val) -> str:
    if isinstance(val, float):
        s = f"{val:.4f}"
        return s.rstrip("0").rstrip(".") if "." in s else s
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (list, tuple)) and len(val) == 2 and all(isinstance(x, float) for x in val):
        # pos-подобные
        a, b = val
        return f"[{_fmt(a)}, {_fmt(b)}]"
    return str(val)

def write_auto_and_migrate(path: Path, di: Diagram, rc: RunConfig) -> None:
    """
    1) Удаляем из каждой секции [[blocks]] старые auto_* строки (всех типов).
    2) Пишем новые auto_* согласно persist_auto_fields (+ freeze_*).
    3) Выполняем миграцию форматов: outs=["B","C"] и глобальные [[arrows]] → [[blocks.outs]].
    4) Сохраняем обратно файл TOML.
    """
    text = read_text(path)
    lines = text.splitlines()
    out: List[str] = []
    i = 0

    # Индексы по id
    by_id: Dict[str, Block] = {b.id: b for b in di.blocks}

    # Удалим всю секцию глобальных [[arrows]] (мы перепишем в blocks.outs)
    # Сначала просто запомним, что она была — и не будем добавлять её в out.
    def is_section_header(ln: str) -> bool:
        t = ln.strip()
        return t.startswith("[") and t.endswith("]")

    def strip_auto_from_section(sec: str) -> str:
        # Убираем любые строки с auto_* на верхнем уровне секции [[blocks]] или её полей.
        pat = re.compile(r'^\s*(?:' + "|".join(map(re.escape, AUTO_KEYS_BLOCK)) + r')\s*=', re.M)
        return "\n".join([ln for ln in sec.splitlines() if not pat.match(ln)])

    # Помощник: записать auto_* обратно в секцию [[blocks]] и её [[blocks.outs]]
    def append_block_auto(sec_text: str, blk: Block) -> str:
        # 1) pos/size
        if "pos" in rc.persist.persist_auto_fields and not (blk.freeze_auto_pos or rc.persist.freeze_auto_pos):
            if blk.pos is None and blk.auto_pos is not None:
                x = clamp01(round_to_grid(blk.auto_pos[0], rc.layout.grid_snap))
                y = clamp01(round_to_grid(blk.auto_pos[1], rc.layout.grid_snap))
                sec_text += f'\nauto_pos = [{_fmt(x)}, {_fmt(y)}]'
        if "size" in rc.persist.persist_auto_fields and not (blk.freeze_auto_size or rc.persist.freeze_auto_size):
            if blk.width is None and blk.auto_width is not None:
                sec_text += f'\nauto_width = {_fmt(blk.auto_width)}'
            if blk.header_height is None and blk.auto_header_height is not None:
                sec_text += f'\nauto_header_height = {_fmt(blk.auto_header_height)}'
            if blk.prop_height is None and blk.auto_prop_height is not None:
                sec_text += f'\nauto_prop_height = {_fmt(blk.auto_prop_height)}'

        # 2) shape/style
        if "shape" in rc.persist.persist_auto_fields and not (blk.freeze_auto_shape or rc.persist.freeze_auto_shape):
            if blk.shape is None and blk.auto_shape is not None:
                sec_text += f'\nauto_shape = {blk.auto_shape!r}'
            if blk.corner_radius is None and blk.auto_corner_radius is not None:
                sec_text += f'\nauto_corner_radius = {_fmt(blk.auto_corner_radius)}'
        if "style" in rc.persist.persist_auto_fields and not (blk.freeze_auto_style or rc.persist.freeze_auto_style):
            if blk.stroke_width is None and blk.auto_stroke_width is not None:
                sec_text += f'\nauto_stroke_width = {_fmt(blk.auto_stroke_width)}'
            if blk.fill is None and blk.auto_fill is not None:
                sec_text += f'\nauto_fill = {blk.auto_fill!r}'
            if blk.stroke is None and blk.auto_stroke is not None:
                sec_text += f'\nauto_stroke = {blk.auto_stroke!r}'

        # 3) fonts
        if "fonts" in rc.persist.persist_auto_fields and not (blk.freeze_auto_fonts or rc.persist.freeze_auto_fonts):
            if blk.font_family is None and blk.auto_font_family is not None:
                sec_text += f'\nauto_font_family = {blk.auto_font_family!r}'
            if blk.font_size_title is None and blk.auto_font_size_title is not None:
                sec_text += f'\nauto_font_size_title = {_fmt(blk.auto_font_size_title)}'
            if blk.font_size_prop is None and blk.auto_font_size_prop is not None:
                sec_text += f'\nauto_font_size_prop = {_fmt(blk.auto_font_size_prop)}'
            if blk.font_bold_title is None and blk.auto_font_bold_title is not None:
                sec_text += f'\nauto_font_bold_title = {_fmt(blk.auto_font_bold_title)}'
            if blk.font_italic_arrow is None and blk.auto_font_italic_arrow is not None:
                sec_text += f'\nauto_font_italic_arrow = {_fmt(blk.auto_font_italic_arrow)}'

        # 4) text (align/valign/padding)
        if "text" in rc.persist.persist_auto_fields and not (blk.freeze_auto_text or rc.persist.freeze_auto_text):
            if blk.text_align_title is None and blk.auto_text_align_title is not None:
                sec_text += f'\nauto_text_align_title = {blk.auto_text_align_title!r}'
            if blk.text_align_props is None and blk.auto_text_align_props is not None:
                sec_text += f'\nauto_text_align_props = {blk.auto_text_align_props!r}'
            if blk.text_valign_title is None and blk.auto_text_valign_title is not None:
                sec_text += f'\nauto_text_valign_title = {blk.auto_text_valign_title!r}'
            if blk.text_valign_props is None and blk.auto_text_valign_props is not None:
                sec_text += f'\nauto_text_valign_props = {blk.auto_text_valign_props!r}'
            if blk.text_padding_title_x is None and blk.auto_text_padding_title_x is not None:
                sec_text += f'\nauto_text_padding_title_x = {_fmt(blk.auto_text_padding_title_x)}'
            if blk.text_padding_title_y is None and blk.auto_text_padding_title_y is not None:
                sec_text += f'\nauto_text_padding_title_y = {_fmt(blk.auto_text_padding_title_y)}'
            if blk.text_padding_prop_x is None and blk.auto_text_padding_prop_x is not None:
                sec_text += f'\nauto_text_padding_prop_x = {_fmt(blk.auto_text_padding_prop_x)}'
            if blk.text_padding_prop_y is None and blk.auto_text_padding_prop_y is not None:
                sec_text += f'\nauto_text_padding_prop_y = {_fmt(blk.auto_text_padding_prop_y)}'
        return sec_text

    # Для удобства сформируем словарь исходящих связей по блокам из ТЕКУЩЕГО Diagram
    outs_map: Dict[str, List[Arrow]] = {}
    for a in di.arrows:
        outs_map.setdefault(a.from_id, []).append(a)

    # Проходим по строкам TOML и точечно модифицируем [[blocks]] секции
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # пропускаем глобальные [[arrows]] секции целиком
        if stripped.startswith("[[arrows]]"):
            # скипаем до следующего заголовка
            j = i + 1
            while j < len(lines) and not is_section_header(lines[j]):
                j += 1
            i = j  # не добавляя ничего в out (удалили секцию)
            continue

        out.append(line)

        if stripped.startswith("[[blocks]]"):
            # собрать тело секции [[blocks]]
            j = i + 1
            sect = [line]
            while j < len(lines) and not is_section_header(lines[j]):
                sect.append(lines[j]); j += 1

            sec_text = "\n".join(sect)

            # извлечь id
            m = re.search(r'^\s*id\s*=\s*"(.*?)"\s*$', sec_text, re.M)
            if m:
                bid = m.group(1)
                blk = by_id.get(bid)
                if blk:
                    # 1) Удаляем старые auto_* строки
                    sec_text = strip_auto_from_section(sec_text)

                    # 2) Мигрируем outs=["B","C"] в [[blocks.outs]]
                    #    и синхронизируем содержимое [[blocks.outs]] с текущей моделью `outs_map[bid]`
                    #    Для простоты: удалим старые вложенные секции [[blocks.outs]] и создадим заново.
                    #    (Это гарантирует чистую структуру.)
                    #    Удалить все [[blocks.outs]]:
                    sec_lines = sec_text.splitlines()
                    cleaned: List[str] = []
                    k = 0
                    while k < len(sec_lines):
                        ln = sec_lines[k]
                        if ln.strip().startswith("[[blocks.outs]]"):
                            # пропустить до следующего заголовка/конца секции [[blocks]]
                            k += 1
                            while k < len(sec_lines) and not sec_lines[k].strip().startswith("["):
                                k += 1
                            continue
                        cleaned.append(ln)
                        k += 1
                    sec_text = "\n".join(cleaned)

                    # вставим новые [[blocks.outs]] из модели
                    if bid in outs_map:
                        for a in outs_map[bid]:
                            # Ручные стили не меняем, авто — несем, если есть
                            sec_text += "\n[[blocks.outs]]"
                            sec_text += f'\n to = "{a.to_id}"'
                            if a.label is not None:
                                sec_text += f'\n label = {a.label!r}'
                            if a.style_curve is not None:
                                sec_text += f'\n style.curve = {a.style_curve!r}'
                            if a.style_label_offset is not None:
                                sec_text += f'\n style.label_offset = {_fmt(a.style_label_offset)}'
                            if a.style_connector_from is not None:
                                sec_text += f'\n style.connector_from = {a.style_connector_from!r}'
                            if a.style_connector_to is not None:
                                sec_text += f'\n style.connector_to = {a.style_connector_to!r}'

                            # авто-часть (без freeze для стрелок — глобально не замораживаем их сейчас)
                            if a.auto_curve is not None:
                                sec_text += f'\n auto_curve = {a.auto_curve!r}'
                            if a.auto_label_offset is not None:
                                sec_text += f'\n auto_label_offset = {_fmt(a.auto_label_offset)}'
                            if a.auto_connector_from is not None:
                                sec_text += f'\n auto_connector_from = {a.auto_connector_from!r}'
                            if a.auto_connector_to is not None:
                                sec_text += f'\n auto_connector_to = {a.auto_connector_to!r}'

                    # 3) Записываем новые auto_* блока (с учётом freeze_* и persist_auto_fields)
                    sec_text = append_block_auto(sec_text, blk)

                    # 4) Заменяем секцию в out
                    sec_new_lines = sec_text.splitlines()
                    out[-1] = sec_new_lines[0]  # [[blocks]]
                    out.extend(sec_new_lines[1:])
                    i = j
                    continue

        i += 1

    new_text = "\n".join(out)
    if rc.persist.create_backup:
        make_backup(path)
    write_text(path, new_text)
    print("INFO: migrated/auto-written:", path.name)


# =============== поиск входных файлов ===============

def discover_files(rc: RunConfig) -> List[Path]:
    files: List[Path] = []
    for base in rc.input_dirs:
        basep = Path(base)
        if not basep.exists():
            continue
        it = basep.rglob("*") if rc.recursive else basep.glob("*")
        for p in it:
            if p.is_file() and p.suffix.lower().lstrip(".") in rc.include_extensions:
                rel = str(p).replace("\\", "/")
                if any(fnmatch(rel, pat) for pat in rc.exclude_patterns):
                    continue
                files.append(p)
    return files


# =============== основной цикл ===============

def process_file(path: Path, rc: RunConfig) -> None:
    print(f"[..] {path.name}")
    di = parse_diagram(path)

    # 1) Начальная раскладка (ставит auto_pos для нефунксов)
    if rc.layout.mode == "layered":
        layered_layout(di, rc)

    # 2) Проставим авто-дефолты для размеров/формы/шрифтов/текста, если нет ручных
    for b in di.blocks:
        # size
        if b.width is None and b.auto_width is None:
            b.auto_width = rc.defaults.block_width
        if b.header_height is None and b.auto_header_height is None:
            b.auto_header_height = rc.defaults.block_header_height
        if b.prop_height is None and b.auto_prop_height is None:
            b.auto_prop_height = rc.defaults.block_prop_height
        # shape/style
        if b.shape is None and b.auto_shape is None:
            b.auto_shape = rc.defaults.block_shape
        if b.corner_radius is None and b.auto_corner_radius is None:
            b.auto_corner_radius = rc.defaults.block_corner_radius
        if b.stroke_width is None and b.auto_stroke_width is None:
            b.auto_stroke_width = rc.defaults.block_stroke_width
        if b.fill is None and b.auto_fill is None:
            b.auto_fill = rc.defaults.block_fill
        if b.stroke is None and b.auto_stroke is None:
            b.auto_stroke = rc.defaults.block_stroke
        # fonts
        if b.font_family is None and b.auto_font_family is None:
            b.auto_font_family = rc.defaults.font_family
        if b.font_size_title is None and b.auto_font_size_title is None:
            b.auto_font_size_title = rc.defaults.font_size_title
        if b.font_size_prop is None and b.auto_font_size_prop is None:
            b.auto_font_size_prop = rc.defaults.font_size_prop
        if b.font_bold_title is None and b.auto_font_bold_title is None:
            b.auto_font_bold_title = rc.defaults.font_bold_title
        if b.font_italic_arrow is None and b.auto_font_italic_arrow is None:
            b.auto_font_italic_arrow = rc.defaults.font_italic_arrow
        # text
        if b.text_align_title is None and b.auto_text_align_title is None:
            b.auto_text_align_title = rc.defaults.text_align_title
        if b.text_align_props is None and b.auto_text_align_props is None:
            b.auto_text_align_props = rc.defaults.text_align_props
        if b.text_valign_title is None and b.auto_text_valign_title is None:
            b.auto_text_valign_title = rc.defaults.text_valign_title
        if b.text_valign_props is None and b.auto_text_valign_props is None:
            b.auto_text_valign_props = rc.defaults.text_valign_props
        if b.text_padding_title_x is None and b.auto_text_padding_title_x is None:
            b.auto_text_padding_title_x = rc.defaults.text_padding_title_x
        if b.text_padding_title_y is None and b.auto_text_padding_title_y is None:
            b.auto_text_padding_title_y = rc.defaults.text_padding_title_y
        if b.text_padding_prop_x is None and b.auto_text_padding_prop_x is None:
            b.auto_text_padding_prop_x = rc.defaults.text_padding_prop_x
        if b.text_padding_prop_y is None and b.auto_text_padding_prop_y is None:
            b.auto_text_padding_prop_y = rc.defaults.text_padding_prop_y

    # 3) Пиксели
    W, H = compute_px(di, rc.defaults)

    # 4) Разводка
    if rc.layout.avoid_node_overlap:
        resolve_overlaps(di, rc, W, H)

    # 5) Рендер SVG (+ PNG)
    out_svg = path.with_suffix(".svg")
    svg = render_svg(di, rc.defaults, out_svg)
    if rc.output.save_png and _HAS_CAIROSVG:
        try:
            cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                             write_to=str(path.with_suffix(".png")),
                             dpi=rc.output.png_dpi)
        except Exception as e:
            print("WARN: PNG экспорт через cairosvg не выполнен:", e)

    # 6) Запись auto_* и миграция формата в файл
    write_auto_and_migrate(path, di, rc)

    # 7) Открыть SVG
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
        print("WARN: не найдено TOML-файлов. Проверьте input_dirs в run.toml.")
        return

    for f in files:
        process_file(f, rc)

    print("Готово.")

if __name__ == "__main__":
    main()
