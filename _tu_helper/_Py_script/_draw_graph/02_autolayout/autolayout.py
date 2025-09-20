#!/usr/bin/env python3
# 02_autolayout / autolayout.py
# Материализация дефолтов [defaults] -> поля блока (write=["size"]) и сохранение <name><output_suffix>.toml

import sys, re, fnmatch
import tomllib
from pathlib import Path

def find_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns) -> list[Path]:
    files: list[Path] = []
    for d in input_dirs:
        base = Path(d)
        if not base.exists():
            print(f"WARN: input dir not found: {base}")
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
            skip = False
            for pat in (exclude_patterns or []):
                if fnmatch.fnmatch(str(p), pat):
                    skip = True
                    break
            if skip:
                continue
            files.append(p)
    return files

def materialize_size_defaults(text: str, defaults: dict, mode: str) -> str:
    width = defaults.get("block.width", defaults.get("block_width", None))
    hh = defaults.get("block_header_height", None)
    ph = defaults.get("block_prop_height", None)

    def replace_or_add(lines: list[str], key: str, val) -> list[str]:
        key_re = re.compile(rf'^\s*{re.escape(key)}\s*=\s*', re.I)
        found = False
        for i, ln in enumerate(lines):
            if key_re.match(ln):
                found = True
                if mode == "overwrite":
                    lines[i] = f"{key} = {val}\n"
                break
        if not found and mode in ("fill", "overwrite"):
            lines.append(f"{key} = {val}\n")
        return lines

    out_lines: list[str] = []
    lines = text.splitlines(keepends=True)
    inside_block = False
    block_buf: list[str] = []

    def flush_block():
        nonlocal out_lines, block_buf
        out_lines.extend(block_buf)
        block_buf = []

    for ln in lines:
        if ln.strip().startswith("[[blocks]]"):
            if inside_block:
                if width is not None:
                    block_buf = replace_or_add(block_buf, "width", width)
                if hh is not None:
                    block_buf = replace_or_add(block_buf, "header_height", hh)
                if ph is not None:
                    block_buf = replace_or_add(block_buf, "prop_height", ph)
                flush_block()
            inside_block = True
            block_buf = [ln]
            continue
        if inside_block:
            if ln.strip().startswith("[[blocks.") or ln.strip().startswith("[[") or (ln.startswith("[") and not ln.startswith("[[blocks")):
                if width is not None:
                    block_buf = replace_or_add(block_buf, "width", width)
                if hh is not None:
                    block_buf = replace_or_add(block_buf, "header_height", hh)
                if ph is not None:
                    block_buf = replace_or_add(block_buf, "prop_height", ph)
                flush_block()
                out_lines.append(ln)
                inside_block = ln.strip().startswith("[[blocks]]")
                if inside_block:
                    block_buf = [ln]
                continue
            else:
                block_buf.append(ln)
                continue
        out_lines.append(ln)

    if inside_block:
        if width is not None:
            block_buf = replace_or_add(block_buf, "width", width)
        if hh is not None:
            block_buf = replace_or_add(block_buf, "header_height", hh)
        if ph is not None:
            block_buf = replace_or_add(block_buf, "prop_height", ph)
        flush_block()

    return "".join(out_lines)

def main():
    cfg_path = Path(__file__).with_name("config_autolayout.toml")
    if not cfg_path.exists():
        print(f"ERR: config not found: {cfg_path}")
        sys.exit(2)
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    io_cfg = cfg.get("io", {})
    input_dirs = io_cfg.get("input_dirs", [])
    recursive = bool(io_cfg.get("recursive", True))
    input_suffix = str(io_cfg.get("input_suffix", ".s01.prepared.toml"))
    include_exts = io_cfg.get("include_extensions", ["toml"])
    exclude_patterns = io_cfg.get("exclude_patterns", [])
    output_suffix = str(io_cfg.get("output_suffix", "_02"))
    write_mode = io_cfg.get("write_mode", "new")
    backup_original = bool(io_cfg.get("backup_original", False))
    dry_run = bool(io_cfg.get("dry_run", False))
    stop_on_error = bool(io_cfg.get("stop_on_error", True))

    defaults = cfg.get("defaults", {})
    pd = cfg.get("persist", {}).get("defaults", {})
    write_groups = set(pd.get("write", []))
    mode = pd.get("mode", "fill")

    files = find_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns)
    print(f"Found {len(files)} file(s).")

    total_ok = 0
    for src in files:
        try:
            text = src.read_text(encoding="utf-8")
            out_text = text

            if "size" in write_groups:
                flat = {}
                for k, v in defaults.items():
                    if isinstance(v, (int, float)):
                        flat[k] = v
                    elif isinstance(v, str):
                        flat[k] = f'"{v}"'
                    else:
                        flat[k] = v
                if "block.width" in defaults and isinstance(defaults["block.width"], (int, float)):
                    flat["block.width"] = defaults["block.width"]
                out_text = materialize_size_defaults(out_text, flat, mode)

            if write_mode == "inplace":
                out_path = src
                if backup_original and not dry_run:
                    bak = src.with_suffix(src.suffix + ".bak")
                    if not bak.exists():
                        bak.write_text(text, encoding="utf-8")
            else:
                base = src.name[:-5] if src.name.endswith(".toml") else src.name
                out_name = f"{base}{output_suffix}.toml"
                out_path = src.with_name(out_name)

            if dry_run:
                print(f"DRY-RUN: would write -> {out_path}")
            else:
                out_text = out_text if out_text.endswith("\n") else (out_text + "\n")
                out_path.write_text(out_text, encoding="utf-8")
                print(f"OK: {src.name} -> {out_path.name}")
            total_ok += 1
        except Exception as e:
            print(f"ERR processing {src}: {e}")
            if stop_on_error:
                sys.exit(1)

    print(f"Done. Written/updated: {total_ok}")

if __name__ == "__main__":
    main()
