#!/usr/bin/env python3
# 03_render / render.py (STRICT)

import sys, fnmatch, math, html, webbrowser
import tomllib
from pathlib import Path

def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

def dotted(D: dict, dotted_key: str, default=None):
    cur = D
    for k in str(dotted_key).split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def discover_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns):
    files = []
    for d in input_dirs:
        base = Path(d)
        if not base.exists(): continue
        it = base.rglob("*") if recursive else base.glob("*")
        for p in it:
            if not p.is_file(): continue
            if include_exts and p.suffix.lstrip(".").lower() not in [e.lower().lstrip(".") for e in include_exts]:
                continue
            if input_suffix and not str(p).endswith(input_suffix):
                continue
            from fnmatch import fnmatch as _fn
            rel = str(p).replace("\\","/")
            if any(_fn(rel, pat) for pat in (exclude_patterns or [])):
                continue
            files.append(p)
    return files

def esc(s): return html.escape(str(s)) if s is not None else ""

def svg_rect(x,y,w,h,fill,stroke,sw,rx):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" ry="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def svg_line(x1,y1,x2,y2,stroke,sw):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"/>'

def svg_text(x,y,text,size,fill,anchor="middle",bold=False,dom_middle=True,family="Arial",italic=False):
    w = "bold" if bold else "normal"
    dom = ' dominant-baseline="middle"' if dom_middle else ""
    fs = f' font-style="italic"' if italic else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-family="{family}" fill="{fill}" font-weight="{w}"{dom}{fs}>{esc(text)}</text>'

def svg_poly(points, stroke, sw):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x,y in points)
    return f'<polyline fill="none" stroke="{stroke}" stroke-width="{sw}" points="{pts}"/>'

def svg_arrow(p1, p2, color, sw, size):
    ang = math.atan2(p2[1]-p1[1], p2[0]-p1[0])
    a1, a2 = ang - math.pi/7, ang + math.pi/7
    x1, y1 = p2[0] - size*math.cos(a1), p2[1] - size*math.sin(a1)
    x2, y2 = p2[0] - size*math.cos(a2), p2[1] - size*math.sin(a2)
    return f'<path d="M {p2[0]:.1f},{p2[1]:.1f} L {x1:.1f},{y1:.1f} M {p2[0]:.1f},{p2[1]:.1f} L {x2:.1f},{y2:.1f}" stroke="{color}" stroke-width="{max(1.0, sw-0.5)}"/>'

def anchor_point(x,y,w,h, side: str):
    s = (side or "center").lower()
    if s == "left":   return (x, y+h/2)
    if s == "right":  return (x+w, y+h/2)
    if s == "top":    return (x+w/2, y)
    if s == "bottom": return (x+w/2, y+h)
    return (x+w/2, y+h/2)

def block_xywh(b, W,H, defaults):
    width  = b.get("width", b.get("auto_width", dotted(defaults,"block.width", 0.10)))
    hh     = b.get("header_height", b.get("auto_header_height", dotted(defaults,"block.header_height", 0.10)))
    ph     = b.get("prop_height",   b.get("auto_prop_height",   dotted(defaults,"block.prop_height", 0.06)))
    propsN = len(b.get("properties") or b.get("props") or [])
    w = max(1.0, float(width) * W)
    h = max(1.0, (float(hh) + float(ph)*propsN) * H)
    pos = b.get("pos", b.get("auto_pos"))
    if not (isinstance(pos,(list,tuple)) and len(pos)==2):
        return None
    cx, cy = float(pos[0])*W, float(pos[1])*H
    x, y = cx - w/2, cy - h/2
    return x,y,w,h, float(hh)*H, float(ph)*H

def main():
    cfg_path = Path(__file__).with_name("config_render.toml")
    if not cfg_path.exists():
        print("ERR: config not found:", cfg_path)
        sys.exit(2)
    cfg = read_toml(cfg_path)

    io = cfg.get("io", {})
    defaults = cfg.get("defaults", {})
    output_cfg = cfg.get("output", {})

    files = discover_files(
        io.get("input_dirs", []),
        bool(io.get("recursive", True)),
        str(io.get("input_suffix", "_02.toml")),
        io.get("include_extensions", ["toml"]),
        io.get("exclude_patterns", []),
    )
    print(f"Found {len(files)} file(s).")

    out_suffix = str(io.get("output_suffix","_03"))
    dry = bool(io.get("dry_run", False))
    open_after = bool(output_cfg.get("open_after_render", False))

    for src in files:
        try:
            g = read_toml(src)
            meta = g.get("meta") or {}
            W,H = (defaults.get("canvas_size",[1200,800])[0], defaults.get("canvas_size",[1200,800])[1])
            if isinstance(meta.get("canvas_size"), list) and len(meta["canvas_size"])==2:
                W,H = int(meta["canvas_size"][0]), int(meta["canvas_size"][1])

            theme_bg = dotted(defaults,"theme.background","#FFFFFF")
            theme_text = dotted(defaults,"theme.text_color","#000000")
            theme_arrow = dotted(defaults,"theme.arrow_color","#222222")
            f_family = dotted(defaults,"font.family","Arial")
            title_size = dotted(defaults,"font.size_title",14)
            prop_size = dotted(defaults,"font.size_prop",12)
            bold_title = bool(dotted(defaults,"font.bold_title",True))
            props_dividers = bool(dotted(defaults,"block.props_dividers", True))
            props_divider_thickness_def = float(dotted(defaults,"block.props_divider_thickness", 0.0))
            italic_arrow = bool(dotted(defaults,"font.italic_arrow",True))
            arrow_size = 6*max(0.5, float(dotted(defaults,"style.arrow_size",1.0)))
            arrow_thickness = float(dotted(defaults,"style.arrow_thickness",2.0))

            blocks = g.get("blocks") or []

            parts = []
            parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
            parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{theme_bg}"/>')
            if meta.get("title"):
                parts.append(svg_text(W/2, 24, meta.get("title"), title_size+2, theme_text, "middle", True, True, f_family))

            geom = []
            id2 = {}
            for b in blocks:
                xywh = block_xywh(b, W,H, defaults)
                if xywh is None:
                    print(f"WARN: block without pos/auto_pos skipped: {b.get('id') or b.get('title')}")
                    continue
                geom.append((b, *xywh))
                bid = b.get("id") or b.get("name") or b.get("key") or b.get("title")
                if bid: id2[str(bid)] = (b, xywh)

            # Блоки + ОДНА разделительная линия между шапкой и списком свойств (между строками свойств полос нет).
            for b,x,y,w,h,HH,PH in geom:
                shape = str(b.get("shape", b.get("auto_shape", dotted(defaults,"block.shape","rounded")))).lower()
                rx = float(b.get("corner_radius", b.get("auto_corner_radius", dotted(defaults,"block.corner_radius",10.0))))
                sw = float(b.get("stroke_width", b.get("auto_stroke_width", dotted(defaults,"block.stroke_width",2.0))))
                fill = str(b.get("fill", b.get("auto_fill", dotted(defaults,"block.fill_color","none"))))
                stroke = str(b.get("stroke", b.get("auto_stroke", dotted(defaults,"block.stroke_color","#000000"))))
                parts.append(svg_rect(x,y,w,h, fill, stroke, sw, rx if shape!="rect" else 0))

                # ОДНА линия между заголовком и свойствами
                parts.append(svg_line(x, y+HH, x+w, y+HH, stroke, max(1.0, sw/2)))

                title = b.get("title") or b.get("id") or ""
                parts.append(svg_text(x+w/2, y+HH/2, title, title_size, theme_text, "middle", bold_title, True, f_family))

                props = b.get("properties") or b.get("props") or []
                for i, line in enumerate(props):
                    py = y+HH + PH*i + PH/2
                    if py > y+h: break
                    parts.append(svg_text(x+w/2, py, line, prop_size, theme_text, "middle", False, True, f_family))
                # Разделители между строками свойств
                if props_dividers and len(props) > 1:
                    dw = props_divider_thickness_def if props_divider_thickness_def > 0 else max(1.0, sw/2)
                    for i in range(len(props)-1):
                        yline = y+HH + PH*(i+1)
                        if yline < y+h:
                            parts.append(svg_line(x, yline, x+w, yline, stroke, dw))
            for b,x,y,w,h,HH,PH in geom:
                outs = b.get("outs") or []
                for o in outs:
                    to_id = o.get("to")
                    tgt = id2.get(str(to_id))
                    if not tgt: 
                        continue
                    tb, (tx,ty,tw,th, tHH, tPH) = tgt
                    cf = (o.get("style.connector_from") or o.get("auto_connector_from") or dotted(defaults,"style.connector_from","right")).lower()
                    ct = (o.get("style.connector_to")   or o.get("auto_connector_to")   or dotted(defaults,"style.connector_to","left")).lower()
                    p1 = anchor_point(x,y,w,h, cf)
                    p2 = anchor_point(tx,ty,tw,th, ct)
                    curve = (o.get("style.curve") or o.get("auto_curve") or dotted(defaults,"style.curve","orthogonal")).lower()
                    if curve == "spline": curve = "orthogonal"
                    if curve == "straight":
                        parts.append(svg_poly([p1,p2], theme_arrow, arrow_thickness))
                    else:
                        mid = (p2[0], p1[1]) if abs(p2[0]-p1[0]) > abs(p2[1]-p1[1]) else (p1[0], p2[1])
                        parts.append(svg_poly([p1, mid, p2], theme_arrow, arrow_thickness))
                    parts.append(svg_arrow(p1,p2, theme_arrow, arrow_thickness, arrow_size))
                    label = o.get("label","")
                    if label is not None:
                        t = float(o.get("style.label_offset", o.get("auto_label_offset", dotted(defaults,"style.label_offset",0.5))))
                        lx = p1[0] + (p2[0]-p1[0])*t
                        ly = p1[1] + (p2[1]-p1[1])*t - 4
                        parts.append(svg_text(lx, ly, label, prop_size, theme_arrow, "middle", False, True, f_family, italic_arrow))

            parts.append("</svg>")
            svg = "\n".join(parts)

            base = src.name[:-5] if src.name.endswith(".toml") else src.stem
            out_svg = src.with_name(base + io.get("output_suffix","_03") + ".svg")
            if dry:
                print("DRY-RUN:", out_svg)
            else:
                out_svg.write_text(svg, encoding="utf-8")
                print("SVG:", out_svg.name)
                if open_after:
                    try:
                        webbrowser.open(out_svg.resolve().as_uri())
                    except Exception as e:
                        print("WARN: cannot open browser:", e)

        except Exception as e:
            print("ERR rendering", src, "->", e)
            if bool(io.get("stop_on_error", True)):
                sys.exit(1)

if __name__ == "__main__":
    main()