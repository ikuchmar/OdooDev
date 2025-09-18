#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
draw_graph.py — версия без [layout_result.blocks_pos]
-----------------------------------------------------

Главная идея:
- Все, что пользователь задал вручную в [[blocks]]:
    pos, width, header_height, prop_height  — уважаем, НЕ трогаем.
- Все, что скрипт вычисляет сам — хранится как auto_*:
    auto_pos, auto_width, auto_header_height, auto_prop_height
  Эти auto_* скрипт КАЖДЫЙ запуск пересчитывает заново:
    1) перед записью — удаляет старые auto_* из блока;
    2) записывает новые auto_*.

Порядок при чтении одного блока:
- Если есть ручной pos — считаем блок «зафиксированным» по позиции.
  Иначе, если есть auto_pos — используем как старт, но блок НЕ фиксируем.
  Иначе — стартовую позицию поставит раскладка.
- То же самое по размерам: manual width/hh/ph фиксируют размер; auto_* считаются стартом, но будут перезаписаны.

Итог: никаких [layout_result.*] больше нет.
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

# toml из stdlib (Python 3.11+)
try:
    import tomllib  # type: ignore
except Exception as e:
    print("ERROR: Нужен Python 3.11+ (есть модуль tomllib).", e)
    sys.exit(1)

# PNG (не обязательно)
_HAS_CAIROSVG = False
try:
    import cairosvg  # type: ignore
    _HAS_CAIROSVG = True
except Exception:
    pass

# ---------------- утилиты ----------------

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

# --------------- конфиг ---------------

@dataclass
class Defaults:
    canvas_size: Tuple[int, int] = (1200, 800)

    # стиль рёбер/подписей
    style_curve: str = "auto"            # auto|straight|arc|spline
    style_label_offset: float = 0.5      # 0..1
    style_connector_from: str = "auto"   # auto|left|right|top|bottom
    style_connector_to: str = "auto"     # auto|left|right|top|bottom
    style_arrow_size: float = 1.0
    style_arrow_thickness: float = 2.0

    # дефолтные размеры блоков (нормированные)
    block_width: float = 0.22
    block_header_height: float = 0.12
    block_prop_height: float = 0.06

    # оформление
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

    # тема
    theme_background: str = "#FFFFFF"
    theme_text_color: str = "#000000"
    theme_arrow_color: str = "#222222"
    theme_block_fill_color: str = "none"
    theme_block_stroke_color: str = "#000000"

@dataclass
class LayoutCfg:
    mode: str = "layered"              # layered|force|off (force опускаем ради простоты)
    direction: str = "LR"              # LR|RL|TB|BT
    minimize_edge_crossings: bool = True
    avoid_node_overlap: bool = True
    edge_routing: str = "orthogonal"   # straight|orthogonal|spline|auto
    edge_label_placement: str = "smart"
    node_padding: float = 0.02
    grid_snap: float = 0.01
    deterministic: bool = True
    seed: int = 42
    respect_fixed_blocks: bool = True  # уважать ручные pos
    iterations: int = 500
    layer_gap: float = 0.08
    node_gap: float = 0.03

@dataclass
class PersistCfg:
    create_backup: bool = True
    write_block_geometry: bool = True
    # какие auto_* писать (всегда перезаписываются)
    persist_auto_fields: List[str] = field(default_factory=lambda: ["auto_pos","auto_width","auto_header_height","auto_prop_height"])
    # сетка привязки только для pos/auto_pos
    grid_snap: float = 0.01

@dataclass
class OutputCfg:
    save_png: bool = True
    save_svg: bool = True
    png_dpi: int = 200
    open_in_browser: str = "svg"  # none|svg

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

# --------------- данные графа ---------------

@dataclass
class Block:
    id: str
    title: str
    properties: List[str]

    # РУЧНЫЕ (фиксированные пользователем) — если заданы, скрипт их не меняет
    pos: Optional[Tuple[float,float]] = None
    width: Optional[float] = None
    header_height: Optional[float] = None
    prop_height: Optional[float] = None

    # AUTO (скрипт генерирует каждый запуск) — при чтении используем как старт, но перезаписываем
    auto_pos: Optional[Tuple[float,float]] = None
    auto_width: Optional[float] = None
    auto_header_height: Optional[float] = None
    auto_prop_height: Optional[float] = None

    # вычисляемые пиксели
    w_px: float = 0.0
    h_px: float = 0.0
    cx_px: float = 0.0
    cy_px: float = 0.0

    # удобные геттеры «эффективных» значений (ручное > авто > дефолт)
    def eff_width(self, defs: Defaults) -> float:
        return self.width if self.width is not None else (self.auto_width if self.auto_width is not None else defs.block_width)

    def eff_header(self, defs: Defaults) -> float:
        return self.header_height if self.header_height is not None else (self.auto_header_height if self.auto_header_height is not None else defs.block_header_height)

    def eff_prop(self, defs: Defaults) -> float:
        return self.prop_height if self.prop_height is not None else (self.auto_prop_height if self.auto_prop_height is not None else defs.block_prop_height)

    def eff_pos(self) -> Optional[Tuple[float,float]]:
        return self.pos if self.pos is not None else self.auto_pos

@dataclass
class Arrow:
    from_id: str
    to_id: str
    label: Optional[str] = None
    style: Dict[str, object] = field(default_factory=dict)

@dataclass
class Diagram:
    meta: Dict[str, object]
    blocks: List[Block]
    arrows: List[Arrow]

# --------------- чтение run.toml ---------------

def load_run_config(path: Path) -> RunConfig:
    raw = tomllib.loads(read_text(path))
    def get(d, k, default=None):
        return d.get(k, default) if isinstance(d, dict) else default

    rc = RunConfig()
    rc.input_dirs = raw.get("input_dirs", [])
    rc.recursive = raw.get("recursive", True)
    rc.include_extensions = raw.get("include_extensions", ["toml"])
    rc.exclude_patterns = raw.get("exclude_patterns", [])

    L = raw.get("layout", {})
    rc.layout = LayoutCfg(
        mode=get(L,"mode","layered"),
        direction=get(L,"direction","LR"),
        minimize_edge_crossings=get(L,"minimize_edge_crossings",True),
        avoid_node_overlap=get(L,"avoid_node_overlap",True),
        edge_routing=get(L,"edge_routing","orthogonal"),
        edge_label_placement=get(L,"edge_label_placement","smart"),
        node_padding=float(get(L,"node_padding",0.02)),
        grid_snap=float(get(L,"grid_snap",0.01)),
        deterministic=get(L,"deterministic",True),
        seed=int(get(L,"seed",42)),
        respect_fixed_blocks=get(L,"respect_fixed_blocks",True),
        iterations=int(get(L,"iterations",500)),
        layer_gap=float(get(L,"layer_gap",0.08)),
        node_gap=float(get(L,"node_gap",0.03)),
    )

    P = raw.get("persist", {})
    rc.persist = PersistCfg(
        create_backup=get(P,"create_backup",True),
        write_block_geometry=get(P,"write_block_geometry",True),
        persist_auto_fields=get(P,"persist_auto_fields",["auto_pos","auto_width","auto_header_height","auto_prop_height"]),
        grid_snap=float(get(P,"grid_snap",0.01)),
    )

    O = raw.get("output", {})
    rc.output = OutputCfg(
        save_png=get(O,"save_png",True),
        save_svg=get(O,"save_svg",True),
        png_dpi=int(get(O,"png_dpi",200)),
        open_in_browser=get(O,"open_in_browser","svg"),
    )

    D = raw.get("defaults", {})
    rc.defaults = Defaults(
        canvas_size=tuple(get(D,"canvas_size",[1200,800])),
        style_curve=get(D,"style.curve","auto"),
        style_label_offset=float(get(D,"style.label_offset",0.5)),
        style_connector_from=get(D,"style.connector_from","auto"),
        style_connector_to=get(D,"style.connector_to","auto"),
        style_arrow_size=float(get(D,"style.arrow_size",1.0)),
        style_arrow_thickness=float(get(D,"style.arrow_thickness",2.0)),
        block_width=float(get(D,"block.width",0.22)),
        block_header_height=float(get(D,"block.header_height",0.12)),
        block_prop_height=float(get(D,"block.prop_height",0.06)),
        block_corner_radius=float(get(D,"block.corner_radius",10.0)),
        block_stroke_width=float(get(D,"block.stroke_width",2.0)),
        block_fill_color=get(D,"block.fill_color","none"),
        block_stroke_color=get(D,"block.stroke_color","#000000"),
        font_family=get(D,"font.family","Arial"),
        font_size_title=int(get(D,"font.size_title",14)),
        font_size_prop=int(get(D,"font.size_prop",12)),
        font_size_arrow=int(get(D,"font.size_arrow",11)),
        font_bold_title=bool(get(D,"font.bold_title",True)),
        font_italic_arrow=bool(get(D,"font.italic_arrow",True)),
        theme_background=get(D,"theme.background","#FFFFFF"),
        theme_text_color=get(D,"theme.text_color","#000000"),
        theme_arrow_color=get(D,"theme.arrow_color","#222222"),
        theme_block_fill_color=get(D,"theme.block_fill_color","none"),
        theme_block_stroke_color=get(D,"theme.block_stroke_color","#000000"),
    )
    return rc

# --------------- парсинг графа ---------------

def parse_diagram(path: Path) -> Diagram:
    data = tomllib.loads(read_text(path))

    meta = data.get("meta", {})
    blocks_raw = data.get("blocks", []) or []
    arrows_raw = data.get("arrows", []) or []

    blocks: List[Block] = []
    seen = set()

    for b in blocks_raw:
        bid = b.get("id")
        if not bid or bid in seen:
            raise ValueError(f"Дублирующийся/пустой id в {path}")
        seen.add(bid)

        # РУЧНЫЕ поля
        pos = b.get("pos")
        if pos is not None:
            pos = (float(pos[0]), float(pos[1]))

        width = b.get("width")
        header_height = b.get("header_height")
        prop_height = b.get("prop_height")

        # AUTO поля
        auto_pos = b.get("auto_pos")
        if auto_pos is not None:
            auto_pos = (float(auto_pos[0]), float(auto_pos[1]))
        auto_width = b.get("auto_width")
        auto_header_height = b.get("auto_header_height")
        auto_prop_height = b.get("auto_prop_height")

        blocks.append(Block(
            id=bid,
            title=b.get("title",""),
            properties=list(b.get("properties",[])),
            pos=pos,
            width=width,
            header_height=header_height,
            prop_height=prop_height,
            auto_pos=auto_pos,
            auto_width=auto_width,
            auto_header_height=auto_header_height,
            auto_prop_height=auto_prop_height,
        ))

    arrows: List[Arrow] = []
    for a in arrows_raw:
        frm, to = a.get("from"), a.get("to")
        if not frm or not to:
            raise ValueError(f"Стрелка без from/to в {path}")
        style = {}
        for key in ("style.curve","style.label_offset","style.connector_from","style.connector_to"):
            if key in a:
                style[key] = a[key]
        arrows.append(Arrow(from_id=frm, to_id=to, label=a.get("label"), style=style))

    return Diagram(meta=meta, blocks=blocks, arrows=arrows)

# --------------- раскладка (layered) ---------------

def layered_layout(di: Diagram, rc: RunConfig) -> None:
    """ставим pos только тем, у кого НЕТ ручного pos; auto_pos может быть стартом, но будет обновлён."""
    direction = (rc.layout.direction or "LR").upper()
    LR = direction in ("LR", "RL")
    reverse_main = direction in ("RL", "BT")

    incoming: Dict[str,List[str]] = {b.id: [] for b in di.blocks}
    outgoing: Dict[str,List[str]] = {b.id: [] for b in di.blocks}
    ids = {b.id for b in di.blocks}
    for a in di.arrows:
        if a.from_id in ids and a.to_id in ids:
            outgoing[a.from_id].append(a.to_id)
            incoming[a.to_id].append(a.from_id)

    sources = [k for k,v in incoming.items() if not v] or ([di.blocks[0].id] if di.blocks else [])
    layer_of = {bid: math.inf for bid in ids}
    for s in sources: layer_of[s] = 0

    fr = list(sources)
    while fr:
        nf = []
        for u in fr:
            for v in outgoing.get(u, []):
                if layer_of[v] > layer_of[u] + 1:
                    layer_of[v] = layer_of[u] + 1
                    nf.append(v)
        fr = nf
    max_layer = max([0]+[d for d in layer_of.values() if d < math.inf])
    for bid, lv in list(layer_of.items()):
        if lv == math.inf:
            max_layer += 1
            layer_of[bid] = max_layer

    layers: Dict[int,List[str]] = {}
    for bid, lv in layer_of.items():
        layers.setdefault(int(lv), []).append(bid)

    order = sorted(layers.keys())
    if reverse_main: order = list(reversed(order))

    # простая упорядочивающая эвристика
    for i, L in enumerate(order):
        idsL = layers[L]
        if i>0:
            left = layers[order[i-1]]
            pi = {bid:j for j,bid in enumerate(left)}
            idsL.sort(key=lambda b: sum(pi.get(p,0) for p in incoming.get(b,[]))/max(1,len(incoming.get(b,[]))))
        layers[L] = idsL

    S = len(order)
    for si, L in enumerate(order):
        main_t = 0.1 + 0.8*(si/max(1,S-1)) if S>1 else 0.5
        row = layers[L]; m = len(row)
        for j, bid in enumerate(row):
            b = next(bb for bb in di.blocks if bb.id==bid)
            # если ручной pos есть и respect_fixed_blocks = true — не трогаем
            if b.pos is not None and rc.layout.respect_fixed_blocks:
                continue
            # иначе поставим старт (если авто было — оно уже в b.auto_pos)
            if b.eff_pos() is None:
                perp = 0.2 + 0.6*(j/max(1,m-1)) if m>1 else 0.5
                x,y = (main_t, perp) if LR else (perp, main_t)
                if reverse_main:
                    if LR: x = 1.0 - x
                    else:  y = 1.0 - y
                b.auto_pos = (clamp01(x), clamp01(y))

# --------------- геометрия (px) ---------------

def compute_px(di: Diagram, defs: Defaults) -> Tuple[int,int]:
    W,H = defs.canvas_size
    cs = di.meta.get("canvas_size")
    if isinstance(cs, list) and len(cs)==2:
        W,H = int(cs[0]), int(cs[1])
    for b in di.blocks:
        w = b.eff_width(defs)
        hh = b.eff_header(defs)
        ph = b.eff_prop(defs)
        total_h = hh + ph*max(0,len(b.properties))
        eff_pos = b.eff_pos() or (0.5,0.5)
        b.w_px = w*W
        b.h_px = total_h*H
        b.cx_px = eff_pos[0]*W
        b.cy_px = eff_pos[1]*H
    return W,H

# --------------- разводка без наложений ---------------

def resolve_overlaps(di: Diagram, rc: RunConfig, W:int, H:int) -> None:
    LR = (rc.layout.direction or "LR").upper() in ("LR","RL")
    blocks = list(di.blocks)
    blocks.sort(key=(lambda b: b.cx_px) if LR else (lambda b: b.cy_px))

    layer_thresh_px = (rc.layout.layer_gap if rc.layout.layer_gap>0 else 0.08) * (W if LR else H)
    layers: List[List[Block]] = []
    cur: List[Block] = []
    last = None
    for b in blocks:
        m = b.cx_px if LR else b.cy_px
        if last is None or abs(m-last) <= layer_thresh_px:
            cur.append(b)
            last = m if last is None else (last+m)/2
        else:
            layers.append(cur); cur=[b]; last=m
    if cur: layers.append(cur)

    gap_px = (rc.layout.node_gap if rc.layout.node_gap>0 else 0.03) * (H if LR else W)

    for row in layers:
        if LR:
            row.sort(key=lambda b: b.cy_px)
            top,bot = 0.10*H, 0.90*H
            for i,b in enumerate(row):
                if i==0:
                    b.cy_px = max(top + b.h_px/2, min(b.cy_px, bot - b.h_px/2))
                else:
                    pr = row[i-1]
                    miny = pr.cy_px + pr.h_px/2 + gap_px + b.h_px/2
                    b.cy_px = max(b.cy_px, miny)
                    if b.cy_px + b.h_px/2 > bot:
                        b.cy_px = bot - b.h_px/2
            for i in range(len(row)-2,-1,-1):
                curb = row[i]; nxt=row[i+1]
                maxy = nxt.cy_px - nxt.h_px/2 - gap_px - curb.h_px/2
                curb.cy_px = min(curb.cy_px, maxy)
                if curb.cy_px - curb.h_px/2 < top:
                    curb.cy_px = top + curb.h_px/2
        else:
            row.sort(key=lambda b: b.cx_px)
            left,right = 0.10*W, 0.90*W
            for i,b in enumerate(row):
                if i==0:
                    b.cx_px = max(left + b.w_px/2, min(b.cx_px, right - b.w_px/2))
                else:
                    pr = row[i-1]
                    minx = pr.cx_px + pr.w_px/2 + gap_px + b.w_px/2
                    b.cx_px = max(b.cx_px, minx)
                    if b.cx_px + b.w_px/2 > right:
                        b.cx_px = right - b.w_px/2
            for i in range(len(row)-2,-1,-1):
                curb = row[i]; nxt=row[i+1]
                maxx = nxt.cx_px - nxt.w_px/2 - gap_px - curb.w_px/2
                curb.cx_px = min(curb.cx_px, maxx)
                if curb.cx_px - curb.w_px/2 < left:
                    curb.cx_px = left + curb.w_px/2

    # страховка от выхода за края
    pad = 0.02
    minx,maxx = pad*W, (1.0-pad)*W
    miny,maxy = pad*H, (1.0-pad)*H
    for b in di.blocks:
        b.cx_px = max(minx + b.w_px/2, min(b.cx_px, maxx - b.w_px/2))
        b.cy_px = max(miny + b.h_px/2, min(b.cy_px, maxy - b.h_px/2))

    # записываем НАЗАД только в auto_pos (ручной pos не трогаем)
    for b in di.blocks:
        if b.pos is None:  # не зафиксирован вручную
            b.auto_pos = (clamp01(b.cx_px/W), clamp01(b.cy_px/H))

# --------------- отрисовка SVG ---------------

def svg_escape(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def block_xywh(b: Block) -> Tuple[float,float,float,float]:
    x = b.cx_px - b.w_px/2
    y = b.cy_px - b.h_px/2
    return x,y,b.w_px,b.h_px

def render_svg(di: Diagram, defs: Defaults, out_svg: Path) -> str:
    W,H = defs.canvas_size
    cs = di.meta.get("canvas_size")
    if isinstance(cs,list) and len(cs)==2:
        W,H = int(cs[0]), int(cs[1])

    bg = defs.theme_background
    text = defs.theme_text_color
    arrow_color = defs.theme_arrow_color
    block_fill = defs.block_fill_color if defs.block_fill_color!="none" else defs.theme_block_fill_color
    block_stroke = defs.block_stroke_color if defs.block_stroke_color!="#000000" else defs.theme_block_stroke_color

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{bg}"/>')

    title = str(di.meta.get("title") or "")
    if title:
        out.append(f'<text x="{W/2:.1f}" y="24" text-anchor="middle" font-family="{defs.font_family}" font-size="{defs.font_size_title+2}" fill="{text}" font-weight="bold">{svg_escape(title)}</text>')

    # блоки
    for b in di.blocks:
        x,y,w,h = block_xywh(b)
        rr = defs.block_corner_radius
        out.append(f'<rect x="{x:.1f}" y="{y:.1f}" rx="{rr}" ry="{rr}" width="{w:.1f}" height="{h:.1f}" fill="{block_fill}" stroke="{block_stroke}" stroke-width="{defs.block_stroke_width}"/>')
        # линия шапки
        HH = b.eff_header(defs) * H
        out.append(f'<line x1="{x:.1f}" y1="{y+HH:.1f}" x2="{x+w:.1f}" y2="{y+HH:.1f}" stroke="{block_stroke}" stroke-width="{max(1.0, defs.block_stroke_width/2)}"/>')
        # заголовок
        fw = "bold" if defs.font_bold_title else "normal"
        out.append(f'<text x="{x+6:.1f}" y="{y+HH-6:.1f}" font-family="{defs.font_family}" font-size="{defs.font_size_title}" fill="{text}" font-weight="{fw}">{svg_escape(b.title)}</text>')
        # свойства
        PH = b.eff_prop(defs) * H
        for i,prop in enumerate(b.properties):
            yy = y + HH + PH*i
            out.append(f'<line x1="{x:.1f}" y1="{yy:.1f}" x2="{x+w:.1f}" y2="{yy:.1f}" stroke="{block_stroke}" stroke-width="{max(0.5, defs.block_stroke_width/2.5)}"/>')
            out.append(f'<text x="{x+6:.1f}" y="{yy + PH - 6:.1f}" font-family="{defs.font_family}" font-size="{defs.font_size_prop}" fill="{text}">{svg_escape(prop)}</text>')

    # стрелки
    def eff_style(a: Arrow) -> Dict[str,object]:
        es = {
            "curve": defs.style_curve,
            "label_offset": defs.style_label_offset,
            "connector_from": defs.style_connector_from,
            "connector_to": defs.style_connector_to,
        }
        for k,v in a.style.items():
            es[k.split("style.",1)[-1]] = v
        return es

    id2b = {b.id:b for b in di.blocks}
    def conn_pt(b: Block, side: str) -> Tuple[float,float]:
        x,y,w,h = block_xywh(b)
        if side=="left": return (x, y+h/2)
        if side=="right":return (x+w, y+h/2)
        if side=="top":  return (x+w/2, y)
        if side=="bottom":return (x+w/2, y+h)
        return (b.cx_px, b.cy_px)

    def choose_side(p1, p2, pref: str) -> str:
        if pref!="auto": return pref
        dx,dy = p2[0]-p1[0], p2[1]-p1[1]
        return "right" if abs(dx)>=abs(dy) and dx>=0 else ("left" if abs(dx)>=abs(dy) else ("bottom" if dy>=0 else "top"))

    for a in di.arrows:
        if a.from_id not in id2b or a.to_id not in id2b: continue
        b1,b2 = id2b[a.from_id], id2b[a.to_id]
        st = eff_style(a)
        s1 = choose_side((b1.cx_px,b1.cy_px),(b2.cx_px,b2.cy_px), st["connector_from"])
        s2 = choose_side((b2.cx_px,b2.cy_px),(b1.cx_px,b1.cy_px), st["connector_to"])
        p1 = conn_pt(b1,s1); p2 = conn_pt(b2,s2)

        curve = st["curve"]
        if curve=="straight":
            d = f'M {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        elif curve=="orthogonal":
            mid = (p2[0],p1[1]) if abs(p2[0]-p1[0])>abs(p2[1]-p1[1]) else (p1[0],p2[1])
            d = f'M {p1[0]:.1f},{p1[1]:.1f} L {mid[0]:.1f},{mid[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f}'
        else:
            cx = (p1[0]+p2[0])/2; cy=(p1[1]+p2[1])/2
            d = f'M {p1[0]:.1f},{p1[1]:.1f} Q {cx:.1f},{cy:.1f} {p2[0]:.1f},{p2[1]:.1f}'
        out.append(f'<path d="{d}" fill="none" stroke="{arrow_color}" stroke-width="{defs.style_arrow_thickness}"/>')

        # стрелочная головка
        ang = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
        a1,a2 = ang-math.pi/7, ang+math.pi/7
        s = 6*defs.style_arrow_size
        x1,y1 = p2[0]-s*math.cos(a1), p2[1]-s*math.sin(a1)
        x2,y2 = p2[0]-s*math.cos(a2), p2[1]-s*math.sin(a2)
        out.append(f'<path d="M {p2[0]:.1f},{p2[1]:.1f} L {x1:.1f},{y1:.1f} M {p2[0]:.1f},{p2[1]:.1f} L {x2:.1f},{y2:.1f}" stroke="{arrow_color}" stroke-width="{max(1.0, defs.style_arrow_thickness-0.5)}"/>')

        if a.label:
            t = max(0.0, min(1.0, float(st["label_offset"])))
            lx = p1[0] + (p2[0]-p1[0])*t
            ly = p1[1] + (p2[1]-p1[1])*t - 4
            font_style = "italic" if defs.font_italic_arrow else "normal"
            out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" font-family="{defs.font_family}" font-size="{defs.font_size_arrow}" fill="{arrow_color}" font-style="{font_style}">{svg_escape(a.label)}</text>')

    out.append("</svg>")
    svg = "\n".join(out)
    write_text(out_svg, svg)
    return svg

# --------------- запись auto_* в [[blocks]] ---------------

def write_auto_fields_into_blocks(orig: Path, di: Diagram, rc: RunConfig) -> None:
    """
    Удаляем старые auto_* строки из каждой секции [[blocks]] и пишем новые:
      auto_pos = [x,y] (с привязкой к grid_snap)
      auto_width, auto_header_height, auto_prop_height
    Ручные поля (pos/width/header_height/prop_height) НЕ трогаем.
    """
    text = read_text(orig)
    lines = text.splitlines()
    out: List[str] = []
    i = 0

    by_id: Dict[str, Block] = {b.id: b for b in di.blocks}
    want = set(rc.persist.persist_auto_fields)

    def fmt(x: float) -> str:
        s = f"{x:.4f}"
        return s.rstrip("0").rstrip(".") if "." in s else s

    def strip_auto_lines(section: str) -> str:
        # удаляем любые строки начинающиеся на auto_*
        return "\n".join(
            ln for ln in section.splitlines()
            if not re.match(r'^\s*auto_(pos|width|header_height|prop_height)\s*=', ln)
        )

    while i < len(lines):
        line = lines[i]
        out.append(line)

        if line.strip().startswith("[[blocks]]"):
            # собрать секцию
            j = i + 1
            sect = [line]
            while j < len(lines) and not lines[j].strip().startswith("["):
                sect.append(lines[j]); j += 1

            sec_text = "\n".join(sect)
            # найдём id
            m = re.search(r'^\s*id\s*=\s*"(.*?)"\s*$', sec_text, re.M)
            if m:
                bid = m.group(1)
                b = by_id.get(bid)
                if b:
                    # 1) удалить старые auto_* строки
                    sec_text = strip_auto_lines(sec_text)

                    # 2) подготовить новые auto_* значения
                    #    pos записываем ТОЛЬКО если нет ручного pos
                    if "auto_pos" in want and b.pos is None and b.auto_pos is not None:
                        x = clamp01(round_to_grid(b.auto_pos[0], rc.persist.grid_snap))
                        y = clamp01(round_to_grid(b.auto_pos[1], rc.persist.grid_snap))
                        sec_text += f'\nauto_pos = [{fmt(x)}, {fmt(y)}]'
                    if "auto_width" in want and b.width is None:
                        aw = b.auto_width if b.auto_width is not None else b.eff_width(rc.defaults)
                        sec_text += f'\nauto_width = {fmt(aw)}'
                    if "auto_header_height" in want and b.header_height is None:
                        ah = b.auto_header_height if b.auto_header_height is not None else b.eff_header(rc.defaults)
                        sec_text += f'\nauto_header_height = {fmt(ah)}'
                    if "auto_prop_height" in want and b.prop_height is None:
                        ap = b.auto_prop_height if b.auto_prop_height is not None else b.eff_prop(rc.defaults)
                        sec_text += f'\nauto_prop_height = {fmt(ap)}'

                    # заменить секцию в выводе
                    sec_lines = sec_text.splitlines()
                    out[-1] = sec_lines[0]
                    out.extend(sec_lines[1:])
                    i = j
                    continue
        i += 1

    new_text = "\n".join(out)
    if rc.persist.create_backup:
        make_backup(orig)
    write_text(orig, new_text)
    print("INFO: auto_* geometry written")

# --------------- обход входных путей ---------------

def discover_files(rc: RunConfig) -> List[Path]:
    from fnmatch import fnmatch
    res: List[Path] = []
    for base in rc.input_dirs:
        base = Path(base)
        if not base.exists(): continue
        it = base.rglob("*") if rc.recursive else base.glob("*")
        for p in it:
            if p.is_file() and p.suffix.lower().lstrip(".") in rc.include_extensions:
                rel = str(p).replace("\\","/")
                if any(fnmatch(rel, pat) for pat in rc.exclude_patterns): continue
                res.append(p)
    return res

# --------------- основной цикл ---------------

def process_file(path: Path, rc: RunConfig) -> None:
    print(f"[..] {path}")
    di = parse_diagram(path)

    # 1) раскладка (ставим только auto_pos, если нет ручного pos)
    if rc.layout.mode == "layered":
        layered_layout(di, rc)
    # "off" — ничего не делаем

    # 2) размеры: если ручных нет — можно записать авто-дефолты (для повторяемости)
    for b in di.blocks:
        if b.width is None: b.auto_width = b.auto_width or rc.defaults.block_width
        if b.header_height is None: b.auto_header_height = b.auto_header_height or rc.defaults.block_header_height
        if b.prop_height is None: b.auto_prop_height = b.auto_prop_height or rc.defaults.block_prop_height

    # 3) пересчёт px
    W,H = compute_px(di, rc.defaults)

    # 4) разводка (обновит auto_pos для нефиксированных)
    if rc.layout.avoid_node_overlap:
        resolve_overlaps(di, rc, W, H)

    # 5) рендер
    out_svg = path.with_suffix(".svg")
    svg = render_svg(di, rc.defaults, out_svg)
    if rc.output.save_png and _HAS_CAIROSVG:
        try:
            cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(path.with_suffix(".png")), dpi=rc.output.png_dpi)
        except Exception as e:
            print("WARN: PNG export via cairosvg failed:", e)

    # 6) запись auto_* прямо в [[blocks]] (старые auto_* убираем, новые пишем)
    write_auto_fields_into_blocks(path, di, rc)

    # 7) открыть SVG (если нужно)
    if rc.output.open_in_browser == "svg":
        try:
            import webbrowser; webbrowser.open(str(out_svg))
        except Exception:
            pass

    print(f"OK: {path.name} -> {out_svg.name}")

def main() -> None:
    here = Path(__file__).resolve().parent
    run_path = here / "run.toml"
    if not run_path.exists():
        print("ERROR: run.toml не найден рядом со скриптом.")
        sys.exit(2)

    rc = load_run_config(run_path)
    files = discover_files(rc)
    if not files:
        print("WARN: не найдено TOML-файлов (проверь input_dirs).")
        return

    for f in files:
        process_file(f, rc)

    print("Готово.")

if __name__ == "__main__":
    main()
