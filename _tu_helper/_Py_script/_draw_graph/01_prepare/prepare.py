#!/usr/bin/env python3
# 01_prepare / prepare.py
# Нормализация и миграция графов (минимальный рабочий скрипт)
# - Поиск входных файлов по [io]
# - Копирование в <name><output_suffix>.toml рядом с исходником
# - Простая очистка auto_* полей и дедупликация outs=[] (если включено в конфиге)

import sys, re, fnmatch
import tomllib
from pathlib import Path
from typing import List

def find_files(input_dirs: List[str], recursive: bool, input_suffix: str,
               include_exts: List[str], exclude_patterns: List[str]) -> List[Path]:
    files: List[Path] = []
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

def dedupe_outs_in_text(text: str) -> str:
    def dedupe_array(m: re.Match) -> str:
        inner = m.group(1)
        items = [s.strip() for s in inner.split(",") if s.strip()]
        norm, seen = [], set()
        for token in items:
            val = token
            if token.startswith(("'", '"')) and token.endswith(("'", '"')) and len(token) >= 2:
                val = token[1:-1]
            if val not in seen:
                seen.add(val)
                norm.append(val)
        rebuilt = ", ".join([f'"{v}"' for v in norm])
        return f'outs = [{rebuilt}]'
    return re.sub(r'^\s*outs\s*=\s*\[([^\]]*)\]\s*$', dedupe_array, text, flags=re.M)

def wipe_auto_fields(text: str) -> str:
    return re.sub(r'(?m)^\s*auto_[A-Za-z0-9_]+\s*=.*\n?', '', text)

def main():
    cfg_path = Path(__file__).with_name("config_prepare.toml")
    if not cfg_path.exists():
        print(f"ERR: config not found: {cfg_path}")
        sys.exit(2)
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))

    io_cfg = cfg.get("io", {})
    input_dirs = io_cfg.get("input_dirs", [])
    recursive = bool(io_cfg.get("recursive", True))
    input_suffix = str(io_cfg.get("input_suffix", ".toml"))
    include_exts = io_cfg.get("include_extensions", ["toml"])
    exclude_patterns = io_cfg.get("exclude_patterns", [])
    output_suffix = str(io_cfg.get("output_suffix", "_01"))
    write_mode = io_cfg.get("write_mode", "new")
    backup_original = bool(io_cfg.get("backup_original", False))
    dry_run = bool(io_cfg.get("dry_run", False))
    stop_on_error = bool(io_cfg.get("stop_on_error", True))

    mig = cfg.get("migration", {})
    wipe_auto = bool(mig.get("wipe_auto_fields", True))
    dedupe_outs = bool(mig.get("dedupe_outs", True))

    files = find_files(input_dirs, recursive, input_suffix, include_exts, exclude_patterns)
    print(f"Found {len(files)} file(s).")

    total_ok = 0
    for src in files:
        try:
            text = src.read_text(encoding="utf-8")
            original_text = text

            if wipe_auto:
                text = wipe_auto_fields(text)
            if dedupe_outs:
                text = dedupe_outs_in_text(text)

            if write_mode == "inplace":
                out_path = src
                if backup_original and not dry_run:
                    bak = src.with_suffix(src.suffix + ".bak")
                    if not bak.exists():
                        bak.write_text(original_text, encoding="utf-8")
            else:
                base = src.name[:-5] if src.name.endswith(".toml") else src.name
                out_name = f"{base}{output_suffix}.toml"
                out_path = src.with_name(out_name)

            if dry_run:
                print(f"DRY-RUN: would write -> {out_path}")
            else:
                out_path.write_text(text, encoding="utf-8")
                print(f"OK: {src.name} -> {out_path.name}")
            total_ok += 1
        except Exception as e:
            print(f"ERR processing {src}: {e}")
            if stop_on_error:
                sys.exit(1)

    print(f"Done. Written/updated: {total_ok}")

if __name__ == "__main__":
    main()
