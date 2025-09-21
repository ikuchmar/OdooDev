#!/usr/bin/env python3
# 04_master_run / master_run.py
# Оркестратор конвейера: правит конфиги подскриптов и запускает их по шагам.
# Поддержка типов шагов: set_params, run_script, set_params_and_run.
# Конвенция расположения:
#   _draw_graph/
#     01_prepare/
#     02_autolayout/
#     03_render/
#     04_master_run/master_run.py, config_master_run.toml
#
# Скрипт автоматически определяет ROOT как родительскую папку 04_master_run.
# Относительные пути в конфиге трактуются относительно ROOT.
#
# ВНИМАНИЕ: при записи TOML комментарии теряются (простая сериализация). Включите options.backup_configs=true, чтобы сохранить .bak.

from __future__ import annotations
import sys, subprocess, fnmatch, shutil
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # _draw_graph/
CFG_PATH = Path(__file__).with_name("config_master_run.toml")

# ---------------- TOML helpers ----------------
def toml_load(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))

def _toml_quote(s: str) -> str:
    return '"' + str(s).replace('\\','\\\\').replace('"','\\"') + '"'

def _toml_dump_val(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return _toml_quote(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_dump_val(x) for x in v) + "]"
    if isinstance(v, dict):
        # flat dump (one-level), used by _toml_dump
        raise ValueError("Nested dict not allowed here")
    return _toml_quote(str(v))

def _toml_dump(obj: dict) -> str:
    """Очень простой дампер для конфигов этапов. Комментарии не сохраняет."""
    out = []
    # keep insertion order
    for k, v in obj.items():
        if isinstance(v, dict):
            out.append(f"[{k}]")
            out.append(_toml_dump(v))
        else:
            out.append(f"{k} = {_toml_dump_val(v)}")
    return "\n".join(out)

def set_dotted(d: dict, dotted_key: str, value):
    keys = str(dotted_key).split(".")
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = value

def get_dotted(d: dict, dotted_key: str, default=None):
    cur = d
    for k in str(dotted_key).split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

# ---------------- Path helpers ----------------
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
        # если имя без папки — ищем в стандартных подпапках
        if len(sp.parts) == 1:
            for sub in ["01_prepare", "02_autolayout", "03_render", "04_master_run"]:
                p = ROOT / sub / sp.name
                if p.exists():
                    return p
    # По имени target-конфига пытаемся угадать скрипт
    for t in targets or []:
        tp = rpath(t)
        if tp.exists():
            folder = tp.parent
            # эвристика по названию
            name = tp.name.lower()
            if "prepare" in name:
                cand = folder / "prepare.py"
            elif "autolayout" in name:
                cand = folder / "autolayout.py"
            elif "render" in name:
                cand = folder / "render.py"
            else:
                # fallback: любой .py в этой папке
                pys = list(folder.glob("*.py"))
                cand = pys[0] if pys else None
            if cand and cand.exists():
                return cand
    return None

# ---------------- Runner ----------------
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

# ---------------- File operations ----------------
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
            try:
                print(".. delete:", p)
                if not dry:
                    p.unlink(missing_ok=True)
                deleted += 1
            except Exception as e:
                print("!! cannot delete", p, "->", e)
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

    # Глобальные настройки, которые используем для удаления
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

        # 1) set_params
        if stype in ("set_params","set_params_and_run"):
            targets = step.get("targets") or []
            params = step.get("params") or []
            for target in targets:
                tpath = rpath(target)
                if not tpath.exists():
                    print("!! target config not found:", tpath)
                    if not cont: sys.exit(1)
                    else: 
                        continue
                try:
                    data = toml_load(tpath)
                except Exception as e:
                    print("!! cannot read TOML:", tpath, "->", e)
                    if not cont: sys.exit(1)
                    else: 
                        continue
                if do_backup and not dry:
                    backup(tpath)
                # apply params
                for p in params:
                    key = p.get("key")
                    use = str(p.get("use","value")).lower()
                    if use == "global":
                        gkey = p.get("global_key")
                        val = get_dotted(globals_, gkey or key)
                        print(f".. set [{tpath.name}] {key} = (globals:{gkey or key}) -> {val!r}")
                    else:
                        val = p.get("value")
                        print(f".. set [{tpath.name}] {key} = {val!r}")
                    set_dotted(data, key, val)
                # write back
                if dry:
                    print(".. dry-run: not writing", tpath)
                else:
                    # simple dump (one-level sections only): we need a real serializer
                    # fallback: use tomlkit if available? Not allowed → implement mini writer
                    # We'll use a generic dump that handles nested dicts recursively.
                    tpath.write_text(dump_full(data), encoding="utf-8")
                    print(".. written:", tpath.name)

        # 2) run_script
        if stype in ("run_script","set_params_and_run"):
            script = step.get("run", {}).get("script")
            args = step.get("run", {}).get("args") or []
            spath = find_script(script, step.get("targets"))
            if not spath:
                print("!! script not found for step", idx, "hint:", script)
                if not cont: sys.exit(1)
            else:
                rc = run_python(spath, args, pyexe, dry)
                if rc != 0:
                    print("!! script failed with code", rc)
                    if not cont: sys.exit(rc)
                else:
                    print(".. script OK")
                    # 3) cleanup intermediates if enabled
                    if delete_toml_after and input_dirs:
                        # эвристика: если autolayout — удаляем *_01.toml; если render — *_02.toml
                        bn = spath.name.lower()
                        if "autolayout" in bn:
                            clean_intermediate(input_dirs, "_01.toml", dry)
                        elif "render" in bn:
                            clean_intermediate(input_dirs, "_02.toml", dry)

        if halt_after:
            print(".. halt_after=true → stop pipeline here")
            break

    print("\nAll done.")

# --------- Better TOML writer (supports nested dicts & arrays of tables) ---------
def dump_full(d: dict) -> str:
    """TOML serializer supporting nested tables and arrays of tables (list of dicts).
    Comments are not preserved. Order is deterministic by traversal order."""
    out = []

    def is_array_of_tables(v):
        return isinstance(v, list) and len(v) > 0 and all(isinstance(x, dict) for x in v)

    def is_list_of_scalars(v):
        return isinstance(v, list) and (len(v) == 0 or all(not isinstance(x, (dict, list)) for x in v))

    def split_obj(obj: dict):
        scalars = {}
        children = {}
        arrays = {}
        for k, v in obj.items():
            if isinstance(v, dict):
                children[k] = v
            elif is_array_of_tables(v):
                arrays[k] = v
            else:
                scalars[k] = v
        return scalars, children, arrays

    def write_scalars(scalars: dict):
        for k, v in scalars.items():
            # only primitives and list-of-scalars are allowed here
            if isinstance(v, list) and not is_list_of_scalars(v):
                raise ValueError(f"Unsupported list type at key '{k}' (expected list of scalars).")
            out.append(f"{k} = {_toml_dump_val(v)}")

    def write_table(path: str, obj: dict):
        out.append(f"[{path}]")
        scalars, children, arrays = split_obj(obj)
        write_scalars(scalars)
        for ck, cv in children.items():
            write_table(f"{path}.{ck}", cv)
        for ak, av in arrays.items():
            for elem in av:
                write_table_instance(f"{path}.{ak}", elem)

    def write_table_instance(path: str, obj: dict):
        out.append(f"[[{path}]]")
        scalars, children, arrays = split_obj(obj)
        write_scalars(scalars)
        for ck, cv in children.items():
            write_table(f"{path}.{ck}", cv)
        for ak, av in arrays.items():
            for elem in av:
                write_table_instance(f"{path}.{ak}", elem)

    # root
    root_scalars, root_children, root_arrays = split_obj(d)
    write_scalars(root_scalars)
    for k, v in root_children.items():
        write_table(k, v)
    for k, arr in root_arrays.items():
        for elem in arr:
            write_table_instance(k, elem)

    return "".join(out) + ("" if out and not out[-1].endswith("") else "")

if __name__ == "__main__":
    main()

    main()
