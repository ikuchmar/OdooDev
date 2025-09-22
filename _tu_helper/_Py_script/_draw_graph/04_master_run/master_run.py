#!/usr/bin/env python3
# 04_master_run / master_run.py
# Мастер-оркестратор с БЕЗОПАСНОЙ правкой TOML (поиск/замена по ключам).
# - Комментарии и форматирование сохраняются.
# - .bak создаётся ТОЛЬКО если файл действительно меняется.
# - Поддержаны шаги: set_params | run_script | set_params_and_run

from __future__ import annotations
import sys, subprocess, shutil, re
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parent.parent   # _draw_graph/
CFG_PATH = Path(__file__).with_name("config_master_run.toml")

# ---------------- Значения в формате TOML ----------------
def _toml_quote(s: str) -> str:
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'

def _fmt_toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return _toml_quote(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_fmt_toml_value(x) for x in v) + "]"
    return _toml_quote(str(v))

# ---------------- Поиск секций и безопасная вставка ----------------
HEADER_RE  = re.compile(r'^\s*\[([^\]]+)\]\s*$', re.M)      # [a.b]
ARRHDR_RE  = re.compile(r'^\s*\[\[([^\]]+)\]\]\s*$', re.M)  # [[a.b]]

def _find_section_ranges(text: str):
    secs = []
    marks = []
    for m in HEADER_RE.finditer(text):
        marks.append((m.start(), m.end(), m.group(1).strip(), "table"))
    for m in ARRHDR_RE.finditer(text):
        marks.append((m.start(), m.end(), m.group(1).strip(), "array"))
    marks.sort(key=lambda x: x[0])
    if not marks:
        return [(0, len(text), "", "root")]
    if marks[0][0] > 0:
        secs.append((0, marks[0][0], "", "root"))
    for i,(s,e,p,t) in enumerate(marks):
        end = marks[i+1][0] if i+1 < len(marks) else len(text)
        secs.append((s,end,p,t))
    return secs

def _ensure_section(text: str, path: str) -> str:
    if not path:
        return text if text.endswith("\n") else text + "\n"
    for s,e,p,t in _find_section_ranges(text):
        if t != "root" and p.strip() == path.strip():
            return text
    # добавить новую секцию в конец
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    text += f"[{path}]\n"
    return text

def _set_key_in_section(text: str, section_path: str, key: str, value_str: str) -> str:
    secs = _find_section_ranges(text)
    target = None
    for s,e,p,t in secs:
        if (not section_path and t=="root") or (p.strip()==section_path.strip() and t in ("table","array")):
            target = (s,e)
            break
    if not target:
        text = _ensure_section(text, section_path)
        secs = _find_section_ranges(text)
        for s,e,p,t in secs:
            if (not section_path and t=="root") or (p.strip()==section_path.strip() and t in ("table","array")):
                target = (s,e)
                break
    s,e = target
    block = text[s:e]

    # заменить существующий ключ
    key_re = re.compile(rf'^(\s*){re.escape(key)}\s*=\s*(.*?)(\s*(#.*))?\s*$', re.M)
    def _repl(m):
        left = m.group(1) + f"{key} = "
        right_comment = m.group(3) or ""
        return left + value_str + right_comment
    new_block, n = key_re.subn(_repl, block, count=1)
    if n == 0:
        # вставить ключ (после заголовка секции, если есть)
        if block.startswith("["):
            pos = block.find("\n")
            insert_at = pos+1 if pos != -1 else len(block)
        else:
            insert_at = len(block)
        prefix, suffix = block[:insert_at], block[insert_at:]
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        new_block = prefix + f"{key} = {value_str}\n" + suffix

    out = text[:s] + new_block + text[e:]
    return out if out.endswith("\n") else out + "\n"

def safe_set(text: str, dotted_key: str, value) -> str:
    parts = dotted_key.split(".")
    if len(parts) == 1:
        section_path, key = "", parts[0]
    else:
        section_path, key = ".".join(parts[:-1]), parts[-1]
    return _set_key_in_section(text, section_path, key, _fmt_toml_value(value))

# ---------------- Прочие утилиты ----------------
def toml_load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

def rpath(rel: str|Path) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (ROOT / p)

def find_script(script: str|None, targets: list[str]|None) -> Path|None:
    if not script and not targets:
        return None
    if script:
        sp = Path(script)
        if sp.is_absolute():
            return sp
        cand = rpath(sp)
        if cand.exists():
            return cand
        if len(sp.parts) == 1:
            for sub in ["01_prepare", "02_autolayout", "03_render", "04_master_run"]:
                p = ROOT / sub / sp.name
                if p.exists():
                    return p
    for t in (targets or []):
        tp = rpath(t)
        if tp.exists():
            folder = tp.parent
            name = tp.name.lower()
            if "prepare" in name:
                cand = folder / "prepare.py"
            elif "autolayout" in name:
                cand = folder / "autolayout.py"
            elif "render" in name:
                cand = folder / "render.py"
            else:
                pys = list(folder.glob("*.py"))
                cand = pys[0] if pys else None
            if cand and cand.exists():
                return cand
    return None

def run_python(script_path: Path, args: list[str], pyexe: str|None, dry: bool) -> int:
    cmd = [pyexe or sys.executable, str(script_path)] + list(args or [])
    print(">> RUN:", " ".join(cmd))
    if dry:
        return 0
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT))
        return cp.returncode or 0
    except Exception as e:
        print("!! ERROR launching:", e)
        return 1

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(path, bak)
        print(".. backup:", bak.name)

def clean_intermediate(input_dirs: list[str], suffix: str, dry: bool):
    deleted = 0
    for d in input_dirs:
        base = Path(d)
        if not base.exists():
            continue
        for p in base.rglob(f"*{suffix}"):
            print(".. delete:", p)
            if not dry:
                p.unlink(missing_ok=True)
            deleted += 1
    print(f".. deleted {deleted} file(s) with suffix {suffix}")

# ---------------- Main ----------------
def main():
    if not CFG_PATH.exists():
        print("Config not found:", CFG_PATH)
        sys.exit(2)
    cfg = toml_load(CFG_PATH)

    globals_ = cfg.get("globals", {})
    options = cfg.get("options", {})
    steps = cfg.get("steps", [])

    dry = bool(options.get("dry_run", False))
    cont = bool(options.get("continue_on_error", False))
    do_backup = bool(options.get("backup_configs", False))
    pyexe = options.get("python_executable") or None

    input_dirs = globals_.get("input_dirs") or globals_.get("io", {}).get("input_dirs") or []
    delete_toml_after = bool(globals_.get("delete_toml_after", False))

    for idx, step in enumerate(steps, 1):
        stype = str(step.get("type","")).lower()
        skip = bool(step.get("skip", False))
        halt_after = bool(step.get("halt_after", False))
        print(f"\n=== STEP {idx}: {stype} ===")
        if skip:
            print(".. skipped")
            continue

        # 1) set_params (safe edit)
        if stype in ("set_params","set_params_and_run"):
            targets = step.get("targets") or []
            params = step.get("params") or []
            for target in targets:
                tpath = rpath(target)
                if not tpath.exists():
                    print("!! target config not found:", tpath)
                    if not cont: sys.exit(1)
                    else: continue
                text = tpath.read_text(encoding="utf-8")
                original = text
                for p in params:
                    key = p.get("key")
                    use = str(p.get("use","value")).lower()
                    if use == "global":
                        gkey = p.get("global_key") or key
                        val = globals_
                        for part in gkey.split("."):
                            val = val.get(part, {}) if isinstance(val, dict) else None
                        if val is None or isinstance(val, dict):
                            val = p.get("value")
                    else:
                        val = p.get("value")
                    print(f".. set [{tpath.name}] {key} := {val!r}")
                    text = safe_set(text, key, val)
                if text != original:
                    if dry:
                        print(".. dry-run: not writing", tpath)
                    else:
                        if do_backup:
                            backup(tpath)  # <-- .bak ТОЛЬКО если есть изменения
                        tpath.write_text(text if text.endswith("\n") else (text + "\n"), encoding="utf-8")
                        print(".. written:", tpath.name)
                else:
                    print(".. no changes:", tpath.name)

        # 2) run_script
        if stype in ("run_script","set_params_and_run"):
            spath = find_script(step.get("run", {}).get("script"), step.get("targets"))
            args = step.get("run", {}).get("args") or []
            if not spath:
                print("!! script not found for step", idx)
                if not cont: sys.exit(1)
            else:
                rc = run_python(spath, args, pyexe, dry)
                if rc != 0:
                    print("!! script failed with code", rc)
                    if not cont: sys.exit(rc)
                else:
                    print(".. script OK")
                    if delete_toml_after and input_dirs:
                        bn = spath.name.lower()
                        if "autolayout" in bn:
                            clean_intermediate(input_dirs, "_01.toml", dry)
                        elif "render" in bn:
                            clean_intermediate(input_dirs, "_02.toml", dry)

        if halt_after:
            print(".. halt_after=true → stop pipeline here")
            break

    print("\nAll done.")

if __name__ == "__main__":
    main()
