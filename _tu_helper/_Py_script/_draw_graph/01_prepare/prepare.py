#!/usr/bin/env python3
# 01_prepare / prepare.py
# Приводим граф к стабильной структуре: добавляем заглушки, чистим дубли, опционно генерируем id/meta.
# Комментарии исходника не сохраняются (упрощение). Перед каждым [[blocks]] — пустая строка.

import sys, fnmatch, re, unicodedata
import tomllib
from pathlib import Path

def read_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

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
            rel = str(p).replace("\\", "/")
            if any(fnmatch.fnmatch(rel, pat) for pat in (exclude_patterns or [])):
                continue
            files.append(p)
    return files

def slugify(s: str, maxlen: int = 40) -> str:
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii', 'ignore')
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    return s[:maxlen] or "block"

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
        # properties
        props = b.get("properties", [])
        if props is None: props = []
        out.append("properties = [" + ", ".join(_q(x) for x in (props or [])) + "]")
        # outs
        outs = b.get("outs", [])
        if outs is None: outs = []
        if not outs:
            out.append("outs = []")
        for o in outs:
            out.append("[[blocks.outs]]")
            to = o.get("to")
            out.append(f'to = {_q(to) if to is not None else _q("")}')
            if "label" in o and o["label"] is not None:
                out.append(f'label = {_q(o["label"])}')
    return "\n".join(out).strip() + "\n"

def dedupe_outs_list(outs):
    seen = set()
    res = []
    for o in outs:
        to = str(o.get("to") or "")
        label = str(o.get("label") or "")
        key = (to, label)
        if key in seen: 
            continue
        seen.add(key)
        res.append(o)
    return res

def process_file(src: Path, cfg: dict):
    E = cfg.get("ensure", {})
    M = cfg.get("migration", {})
    data = read_toml(src)

    meta = data.get("meta") or {}
    blocks = data.get("blocks") or []

    # add_default_meta
    if E.get("add_default_meta", False):
        if not meta: meta = {}
        if E.get("title_from_filename", True) and not meta.get("title"):
            meta["title"] = src.stem
        if not meta.get("canvas_size"):
            meta["canvas_size"] = list(cfg.get("ensure", {}).get("default_canvas_size", [1200,800]))

    norm_blocks = []
    for idx, rb in enumerate(blocks):
        b = dict(rb)
        # generate_block_ids
        if not b.get("id"):
            mode = str(E.get("generate_block_ids","off")).lower()
            if mode == "slug" and b.get("title"):
                b["id"] = slugify(b["title"], int(E.get("slug_maxlen",40)))
            elif mode == "uuid":
                import uuid
                b["id"] = uuid.uuid4().hex[:8]

        # ensure properties/outs
        if E.get("add_missing_properties", True) and "properties" not in b:
            b["properties"] = []
        if E.get("add_missing_outs", True) and "outs" not in b:
            b["outs"] = []

        # normalize outs list to list[dict]
        outs_in = b.get("outs") or []
        outs_norm = []
        for o in outs_in:
            if isinstance(o, dict):
                oo = {"to": o.get("to")}
                if E.get("force_label_on_outs", False):
                    oo["label"] = "" if o.get("label") is None else str(o.get("label"))
                elif "label" in o:
                    oo["label"] = o.get("label")
                outs_norm.append(oo)
            else:
                oo = {"to": str(o)}
                if E.get("force_label_on_outs", False):
                    oo["label"] = ""
                outs_norm.append(oo)
        if M.get("dedupe_outs", True):
            outs_norm = dedupe_outs_list(outs_norm)
        b["outs"] = outs_norm
        norm_blocks.append(b)

    return {"meta": meta, "blocks": norm_blocks}

def main():
    cfg_path = Path(__file__).with_name("config_prepare.toml")
    if not cfg_path.exists():
        print("ERR: config not found:", cfg_path)
        sys.exit(2)
    cfg = read_toml(cfg_path)

    io = cfg.get("io", {})
    files = discover_files(
        io.get("input_dirs", []),
        bool(io.get("recursive", True)),
        str(io.get("input_suffix", ".toml")),
        io.get("include_extensions", ["toml"]),
        io.get("exclude_patterns", []),
    )
    print(f"Found {len(files)} file(s).")

    out_suffix = str(io.get("output_suffix","_01"))
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
            print("ERR:", src, "->", e)
            if stop_on_error:
                sys.exit(1)
    print("Done. Written:", done)

if __name__ == "__main__":
    main()
