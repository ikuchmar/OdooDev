#!/usr/bin/env python3
# 02_autolayout / autolayout.py
# Генерирует auto_* и (опц.) материализует дефолты в обычные поля.
# Всегда добавляет label в [[blocks.outs]] (пустая строка, если не задан).
import sys, fnmatch, math
import tomllib
from pathlib import Path

def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

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

def dotted(D: dict, dotted_key: str, default=None):
    cur = D
    for k in str(dotted_key).split("."):
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _q(s: str) -> str:
    return '"' + str(s).replace('\\', '\\\\').replace('"','\\"') + '"'

def dump_toml(graph: dict) -> str:
    out = []
    meta = graph.get("meta", {})
    if meta:
        out.append("[meta]")
        for k, v in meta.items():
            if isinstance(v, (list, tuple)):
                vals = ", ".join([_q(x) if isinstance(x,str) else str(x).lower() if isinstance(x,bool) else str(x) for x in v])
                out.append(f"{k} = [{vals}]")
            elif isinstance(v, str):
                out.append(f"{k} = {_q(v)}")
            elif isinstance(v, bool):
                out.append(f"{k} = {str(v).lower()}")
            else:
                out.append(f"{k} = {v}")
        out.append("")

    for b in graph.get("blocks", []):
        out.append("")
        out.append("[[blocks]]")
        for key in ("id","name","key","title"):
            if key in b and b[key] is not None:
                out.append(f'{key} = {_q(b[key])}')
        for key in ("width","header_height","prop_height"):
            if key in b and b[key] is not None:
                out.append(f"{key} = {b[key]}")
        if "pos" in b and isinstance(b["pos"], (list,tuple)) and len(b["pos"])==2:
            out.append(f"pos = [{b['pos'][0]}, {b['pos'][1]}]")
        if "auto_pos" in b and isinstance(b["auto_pos"], (list,tuple)) and len(b["auto_pos"])==2:
            out.append(f"auto_pos = [{b['auto_pos'][0]}, {b['auto_pos'][1]}]")
        for key in (
            "auto_width","auto_header_height","auto_prop_height",
            "auto_shape","auto_corner_radius","auto_stroke_width","auto_fill","auto_stroke",
            "auto_font_family","auto_font_size_title","auto_font_size_prop","auto_font_bold_title","auto_font_italic_arrow",
            "auto_text_align_title","auto_text_align_props","auto_text_valign_title","auto_text_valign_props",
            "auto_text_padding_title_x","auto_text_padding_title_y","auto_text_padding_prop_x","auto_text_padding_prop_y",
            "shape","corner_radius","stroke_width","fill","stroke",
            "font_family","font_size_title","font_size_prop","font_bold_title","font_italic_arrow",
            "text_align_title","text_align_props","text_valign_title","text_valign_props",
            "text_padding_title_x","text_padding_title_y","text_padding_prop_x","text_padding_prop_y",
        ):
            if key in b and b[key] is not None:
                val = b[key]
                if isinstance(val, str):
                    out.append(f"{key} = {_q(val)}")
                elif isinstance(val, bool):
                    out.append(f"{key} = {str(val).lower()}")
                else:
                    out.append(f"{key} = {val}")
        props = b.get("properties") or []
        out.append("properties = [" + ", ".join(_q(x) for x in props) + "]")
        for o in b.get("outs", []):
            out.append("[[blocks.outs]]")
            to = o.get("to")
            out.append(f'to = {_q(to) if to is not None else _q("")}')
            out.append(f'label = {_q(o.get("label",""))}')
            for key in ("auto_connector_from","auto_connector_to","auto_curve","auto_label_offset",
                        "style.connector_from","style.connector_to","style.curve","style.label_offset"):
                if key in o and o[key] is not None:
                    val = o[key]
                    if isinstance(val, str):
                        out.append(f"{key} = {_q(val)}")
                    elif isinstance(val, bool):
                        out.append(f"{key} = {str(val).lower()}")
                    else:
                        out.append(f"{key} = {val}")
    return "\n".join(out).rstrip() + "\n"

def build_group_flags(persist_cfg: dict):
    groups = { "pos":False,"size":False,"shape":False,"fonts":False,"text":False,"edge_style":False }
    freeze = { k:False for k in groups }
    for g in persist_cfg.get("groups", []):
        name = str(g.get("name","")).lower()
        if name in groups:
            groups[name] = bool(g.get("save", False))
            freeze[name] = bool(g.get("freeze", False))
    mat = (persist_cfg.get("defaults", {}) or {}).get("materialize", [])
    mode = (persist_cfg.get("defaults", {}) or {}).get("mode", "fill")
    mat_set = {str(x).lower() for x in (mat or [])}
    return groups, freeze, mat_set, str(mode).lower()

def layered_positions(blocks: list, layout: dict):
    mode = str(layout.get("mode","layered")).lower()
    if mode == "off":
        return
    direction = str(layout.get("direction","LR")).upper()
    respect_fixed = bool(layout.get("respect_fixed_blocks", True))

    id2i = { (b.get("id") or f"b{i}") : i for i,b in enumerate(blocks) }
    incoming = {i: [] for i in range(len(blocks))}
    outgoing = {i: [] for i in range(len(blocks))}
    for i,b in enumerate(blocks):
        for o in b.get("outs", []):
            j = id2i.get(o.get("to"))
            if j is not None:
                outgoing[i].append(j)
                incoming[j].append(i)

    INF = 10**9
    layer = [INF]*len(blocks)
    srcs = [i for i in range(len(blocks)) if not incoming[i]] or ([0] if blocks else [])
    front = []
    for s in srcs: layer[s]=0; front.append(s)
    while front:
        nf = []
        for u in front:
            for v in outgoing[u]:
                if layer[v] > layer[u]+1:
                    layer[v] = layer[u]+1
                    nf.append(v)
        front = nf
    mx = 0
    for i,lv in enumerate(layer):
        if lv == INF:
            mx += 1; layer[i] = mx
        else:
            mx = max(mx, lv)

    by_layer = {}
    for i,lv in enumerate(layer):
        by_layer.setdefault(lv, []).append(i)
    order = sorted(by_layer.keys())
    LR = direction in ("LR","RL")
    reverse_main = direction in ("RL","BT")
    S = len(order)

    for si,L in enumerate(order):
        main_t = 0.5 if S<=1 else max(0.1, min(0.9, 0.1 + 0.8*(si/(S-1))))
        row = by_layer[L]; m = len(row)
        for idx,j in enumerate(row):
            b = blocks[j]
            if respect_fixed and isinstance(b.get("pos"), (list,tuple)) and len(b["pos"])==2:
                continue
            perp = 0.5 if m<=1 else max(0.1, min(0.9, 0.1 + 0.8*(idx/(m-1))))
            x,y = (main_t, perp) if LR else (perp, main_t)
            if reverse_main:
                if LR: x = 1.0-x
                else:  y = 1.0-y
            b["auto_pos"] = [round(x,4), round(y,4)]

def process_file(src: Path, cfg: dict):
    defaults = cfg.get("defaults", {})
    layout = cfg.get("layout", {})
    groups, freeze, mat_set, mat_mode = build_group_flags(cfg.get("persist", {}))

    data = read_toml(src)
    meta = data.get("meta") or {}
    blocks_in = data.get("blocks") or []

    defd = {
        "width":          float(dotted(defaults,"block.width", 0.10)),
        "header_height":  float(dotted(defaults,"block.header_height", 0.10)),
        "prop_height":    float(dotted(defaults,"block.prop_height", 0.06)),
        "shape":          str(dotted(defaults,"block.shape", "rounded")),
        "corner_radius":  float(dotted(defaults,"block.corner_radius", 10.0)),
        "stroke_width":   float(dotted(defaults,"block.stroke_width", 2.0)),
        "fill":           str(dotted(defaults,"block.fill_color", "none")),
        "stroke":         str(dotted(defaults,"block.stroke_color", "#000000")),
        "font_family":    str(dotted(defaults,"font.family", "Arial")),
        "font_size_title":int(dotted(defaults,"font.size_title", 14)),
        "font_size_prop": int(dotted(defaults,"font.size_prop", 12)),
        "font_bold_title":bool(dotted(defaults,"font.bold_title", True)),
        "font_italic_arrow":bool(dotted(defaults,"font.italic_arrow", True)),
        "text_align_title": str(dotted(defaults,"block.text_align_title", "center")),
        "text_align_props": str(dotted(defaults,"block.text_align_props", "center")),
        "text_valign_title":str(dotted(defaults,"block.text_valign_title", "middle")),
        "text_valign_props":str(dotted(defaults,"block.text_valign_props", "middle")),
        "text_padding_title_x": float(dotted(defaults,"block.text_padding_title_x", 6)),
        "text_padding_title_y": float(dotted(defaults,"block.text_padding_title_y", 6)),
        "text_padding_prop_x":  float(dotted(defaults,"block.text_padding_prop_x", 6)),
        "text_padding_prop_y":  float(dotted(defaults,"block.text_padding_prop_y", 6)),
        "connector_from": str(dotted(defaults,"style.connector_from", "right")).lower(),
        "connector_to":   str(dotted(defaults,"style.connector_to",   "left")).lower(),
        "curve":          str(dotted(defaults,"style.curve", "orthogonal")).lower(),
        "label_offset":   float(dotted(defaults,"style.label_offset", 0.5)),
    }

    blocks = []
    for rb in blocks_in:
        b = {}
        for k in ("id","name","key","title"):
            if k in rb: b[k] = rb.get(k)
        for k in ("width","header_height","prop_height","pos"):
            if k in rb: b[k] = rb.get(k)

        props = rb.get("properties", rb.get("props", []))
        if isinstance(props, dict):
            b["properties"] = [f"{k}: {v}" for k,v in props.items()]
        elif isinstance(props, list):
            b["properties"] = [str(x) for x in props]

        # --- AUTO groups ---
        if groups.get("size") and not freeze.get("size"):
            b["auto_width"] = float(defd["width"])
            b["auto_header_height"] = float(defd["header_height"])
            b["auto_prop_height"] = float(defd["prop_height"])

        if groups.get("shape") and not freeze.get("shape"):
            b["auto_shape"] = defd["shape"]
            b["auto_corner_radius"] = float(defd["corner_radius"])
            b["auto_stroke_width"] = float(defd["stroke_width"])
            b["auto_fill"] = defd["fill"]
            b["auto_stroke"] = defd["stroke"]

        if groups.get("fonts") and not freeze.get("fonts"):
            b["auto_font_family"] = defd["font_family"]
            b["auto_font_size_title"] = int(defd["font_size_title"])
            b["auto_font_size_prop"]  = int(defd["font_size_prop"])
            b["auto_font_bold_title"] = bool(defd["font_bold_title"])
            b["auto_font_italic_arrow"] = bool(defd["font_italic_arrow"])

        if groups.get("text") and not freeze.get("text"):
            b["auto_text_align_title"] = defd["text_align_title"]
            b["auto_text_align_props"] = defd["text_align_props"]
            b["auto_text_valign_title"] = defd["text_valign_title"]
            b["auto_text_valign_props"] = defd["text_valign_props"]
            b["auto_text_padding_title_x"] = float(defd["text_padding_title_x"])
            b["auto_text_padding_title_y"] = float(defd["text_padding_title_y"])
            b["auto_text_padding_prop_x"]  = float(defd["text_padding_prop_x"])
            b["auto_text_padding_prop_y"]  = float(defd["text_padding_prop_y"])

        outs_in = rb.get("outs", [])
        outs = []
        for o in outs_in or []:
            if isinstance(o, dict):
                to = o.get("to")
                label = o.get("label")
                oo = {"to": str(to) if to is not None else ""}
                oo["label"] = "" if label is None else str(label)  # ВСЕГДА пишем label
                if groups.get("edge_style") and not freeze.get("edge_style"):
                    curve = str(o.get("style.curve") or defd["curve"]).lower()
                    if curve == "spline": curve = "orthogonal"
                    oo["auto_curve"] = curve
                    oo["auto_connector_from"] = str(o.get("style.connector_from") or defd["connector_from"]).lower()
                    oo["auto_connector_to"]   = str(o.get("style.connector_to")   or defd["connector_to"]).lower()
                    lo = o.get("style.label_offset")
                    if lo is None: lo = defd["label_offset"]
                    oo["auto_label_offset"] = float(lo)
                outs.append(oo)
            else:
                outs.append({"to": str(o), "label": ""})
        if outs:
            b["outs"] = outs

        blocks.append(b)

    if groups.get("pos") and not freeze.get("pos"):
        layered_positions(blocks, layout)

    # --- MATERIALIZE (в обычные поля) ---
    def fill_or_overwrite(obj: dict, key: str, value):
        if mat_mode == "overwrite" or key not in obj or obj[key] is None:
            obj[key] = value

    for b in blocks:
        if "size" in mat_set:
            fill_or_overwrite(b, "width",          b.get("auto_width", defd["width"]))
            fill_or_overwrite(b, "header_height",  b.get("auto_header_height", defd["header_height"]))
            fill_or_overwrite(b, "prop_height",    b.get("auto_prop_height", defd["prop_height"]))
        if "pos" in mat_set:
            if "auto_pos" in b:
                fill_or_overwrite(b, "pos", b["auto_pos"])
        if "shape" in mat_set:
            fill_or_overwrite(b, "shape",         b.get("auto_shape", defd["shape"]))
            fill_or_overwrite(b, "corner_radius", b.get("auto_corner_radius", defd["corner_radius"]))
            fill_or_overwrite(b, "stroke_width",  b.get("auto_stroke_width", defd["stroke_width"]))
            fill_or_overwrite(b, "fill",          b.get("auto_fill", defd["fill"]))
            fill_or_overwrite(b, "stroke",        b.get("auto_stroke", defd["stroke"]))
        if "fonts" in mat_set:
            fill_or_overwrite(b, "font_family",        b.get("auto_font_family", defd["font_family"]))
            fill_or_overwrite(b, "font_size_title",    b.get("auto_font_size_title", defd["font_size_title"]))
            fill_or_overwrite(b, "font_size_prop",     b.get("auto_font_size_prop", defd["font_size_prop"]))
            fill_or_overwrite(b, "font_bold_title",    b.get("auto_font_bold_title", defd["font_bold_title"]))
            fill_or_overwrite(b, "font_italic_arrow",  b.get("auto_font_italic_arrow", defd["font_italic_arrow"]))
        if "text" in mat_set:
            fill_or_overwrite(b, "text_align_title",     b.get("auto_text_align_title", defd["text_align_title"]))
            fill_or_overwrite(b, "text_align_props",     b.get("auto_text_align_props", defd["text_align_props"]))
            fill_or_overwrite(b, "text_valign_title",    b.get("auto_text_valign_title", defd["text_valign_title"]))
            fill_or_overwrite(b, "text_valign_props",    b.get("auto_text_valign_props", defd["text_valign_props"]))
            fill_or_overwrite(b, "text_padding_title_x", b.get("auto_text_padding_title_x", defd["text_padding_title_x"]))
            fill_or_overwrite(b, "text_padding_title_y", b.get("auto_text_padding_title_y", defd["text_padding_title_y"]))
            fill_or_overwrite(b, "text_padding_prop_x",  b.get("auto_text_padding_prop_x", defd["text_padding_prop_x"]))
            fill_or_overwrite(b, "text_padding_prop_y",  b.get("auto_text_padding_prop_y", defd["text_padding_prop_y"]))
        if "edge_style" in mat_set:
            for o in b.get("outs", []) or []:
                fill_or_overwrite(o, "style.connector_from", o.get("auto_connector_from", defd["connector_from"]))
                fill_or_overwrite(o, "style.connector_to",   o.get("auto_connector_to",   defd["connector_to"]))
                fill_or_overwrite(o, "style.curve",          o.get("auto_curve",          defd["curve"]))
                fill_or_overwrite(o, "style.label_offset",   o.get("auto_label_offset",   defd["label_offset"]))

    return {"meta": meta, "blocks": blocks}

def main():
    cfg_path = Path(__file__).with_name("config_autolayout.toml")
    if not cfg_path.exists():
        print("ERR: config not found:", cfg_path)
        sys.exit(2)
    cfg = read_toml(cfg_path)
    io = cfg.get("io", {})

    files = discover_files(
        io.get("input_dirs", []),
        bool(io.get("recursive", True)),
        str(io.get("input_suffix", "_01.toml")),
        io.get("include_extensions", ["toml"]),
        io.get("exclude_patterns", []),
    )
    print(f"Found {len(files)} file(s).")

    out_suffix = str(io.get("output_suffix","_02"))
    write_mode = str(io.get("write_mode","new")).lower()
    backup = bool(io.get("backup_original", False))
    dry = bool(io.get("dry_run", False))
    stop_on_error = bool(io.get("stop_on_error", True))

    done = 0
    for src in files:
        try:
            new_graph = process_file(src, cfg)
            if write_mode == "inplace":
                out_path = src
                if backup:
                    bak = src.with_suffix(src.suffix + ".bak")
                    if not bak.exists():
                        bak.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                base = src.name[:-5] if src.name.endswith(".toml") else src.stem
                out_path = src.with_name(base + out_suffix + ".toml")
            if dry:
                print("DRY-RUN:", out_path)
            else:
                out_text = dump_toml(new_graph)
                out_path.write_text(out_text, encoding="utf-8")
                print("OK:", src.name, "->", out_path.name)
            done += 1
        except Exception as e:
            print("ERR processing", src, "->", e)
            if stop_on_error: sys.exit(1)
    print("Done. Written:", done)

if __name__ == "__main__":
    main()
