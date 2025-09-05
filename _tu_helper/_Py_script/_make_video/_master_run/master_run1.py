#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мастер-скрипт: запускается без параметров, читает master_config.toml,
выполняет шаги: set_params / run_script / set_params_and_run.
- Параметры берутся из [globals] и переопределяются [steps.step_params].
- Меняем ТОЛЬКО существующие ключи в целевых TOML-файлах (по относительным путям).
- Формат и комментарии в файле сохраняем: замена по строке "key = value".
- Пишем атомарно (tmp + rename), опционально делаем *.bak.
"""

import os
import sys
import re
import subprocess
import shutil
from pathlib import Path

# --- TOML чтение (stdlib tomllib для 3.11+; иначе пробуем tomli) ---
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # fallback (если установлен)
    except ModuleNotFoundError:
        print("Ошибка: ни tomllib (3.11+) ни tomli не найдены. Установите tomli: pip install tomli", file=sys.stderr)
        sys.exit(1)


def load_toml_bytes(p: Path) -> dict:
    with p.open('rb') as f:
        return tomllib.load(f)


def read_text(p: Path) -> str:
    return p.read_text(encoding='utf-8')


def atomic_write_text(p: Path, data: str, backup: bool):
    if backup and p.exists():
        bak = p.with_suffix(p.suffix + ".bak")
        try:
            shutil.copy2(p, bak)
        except Exception as e:
            print(f"[WARN] Не удалось создать бэкап {bak}: {e}")
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(data, encoding='utf-8', newline='')
    os.replace(tmp, p)


def python_executable_from_options(options: dict) -> str:
    exe = (options or {}).get("python_executable", "") or sys.executable
    return exe


def to_toml_literal(value):
    """Простая сериализация для строк, чисел, bool, списков."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        val = value.replace('\\\\', '\\\\\\\\').replace('"', '\\"')
        return f'"{val}"'
    if isinstance(value, list):
        items = ", ".join(to_toml_literal(x) for x in value)
        return f"[{items}]"
    raise TypeError(f"Неподдерживаемый тип для TOML: {type(value).__name__}")


def replace_key_in_toml_text(toml_text: str, key: str, new_value) -> tuple[str, bool]:
    pattern = re.compile(rf'^(?P<prefix>\\s*){re.escape(key)}\\s*=\\s*(?P<val>.+?)(?P<trail>\\s*)(?P<comment>#.*)?$', re.MULTILINE)
    replaced = False

    def _repl(m):
        nonlocal replaced
        replaced = True
        prefix = m.group('prefix') or ''
        trail = m.group('trail') or ''
        comment = m.group('comment') or ''
        literal = to_toml_literal(new_value)
        return f"{prefix}{key} = {literal}{trail}{comment if comment else ''}"

    new_text, count = pattern.subn(_repl, toml_text)
    return new_text, replaced


def apply_params_to_file(config_path: Path, values: dict, only_keys: list[str] | None) -> dict:
    text = read_text(config_path)
    stats = {'changed': [], 'missing': [], 'skipped': []}

    keys = list(values.keys())
    if only_keys:
        keys = [k for k in keys if k in only_keys]

    for k in keys:
        v = values[k]
        try:
            new_text, ok = replace_key_in_toml_text(text, k, v)
        except TypeError:
            stats['skipped'].append(k)
            continue
        if ok:
            text = new_text
            stats['changed'].append(k)
        else:
            stats['missing'].append(k)

    return text, stats


def merge_step_values(globals_map: dict, step_params: dict | None) -> dict:
    merged = dict(globals_map or {})
    if step_params:
        merged.update(step_params)  # приоритет шага
    return merged


def run_script(python_exe: str, script_path: Path, args: list[str] | None, env: dict | None) -> int:
    cmd = [python_exe, str(script_path)]
    if args:
        cmd.extend(args)
    print(f"[RUN] {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, env=env, cwd=str(script_path.parent))
        return proc.returncode
    except FileNotFoundError as e:
        print(f"[ERROR] Не удалось запустить скрипт {script_path}: {e}")
        return 127


def main():
    root = Path(__file__).resolve().parent  # папка _master_run
    project_root = root.parent              # общий корень проекта (_make_video)
    cfg_path = root / "master_config.toml"
    if not cfg_path.exists():
        print(f"[ERROR] Не найден master_config.toml по пути: {cfg_path}", file=sys.stderr)
        sys.exit(2)

    data = load_toml_bytes(cfg_path)

    globals_map = data.get("globals", {}) or {}
    options = data.get("options", {}) or {}
    steps = data.get("steps", []) or []

    dry_run = bool(options.get("dry_run", False))
    continue_on_error = bool(options.get("continue_on_error", False))
    backup_configs = bool(options.get("backup_configs", True))
    python_exe = python_executable_from_options(options)

    print("[INFO] Старт мастер-скрипта")
    print(f"[INFO] dry_run={dry_run}, continue_on_error={continue_on_error}, backup_configs={backup_configs}")
    print(f"[INFO] Python: {python_exe}")
    print(f"[INFO] Папка мастера: {root}")
    print(f"[INFO] Корень проекта: {project_root}")

    for idx, step in enumerate(steps, start=1):
        stype = (step.get("type") or "").strip()
        print(f"\\n[STEP {idx}] type={stype}")

        if stype not in {"set_params", "run_script", "set_params_and_run"}:
            print(f"[WARN] Неизвестный тип шага: {stype}. Пропуск.")
            continue

        targets = step.get("targets", []) or []
        only_keys = step.get("only_keys", None)
        step_params = step.get("step_params", None)

        script_rel = None
        script_args = None

        if stype == "run_script":
            script_rel = step.get("script")
            script_args = step.get("args", [])
        elif stype == "set_params_and_run":
            run_block = step.get("run", {}) or {}
            script_rel = run_block.get("script")
            script_args = run_block.get("args", [])

        if stype in {"set_params", "set_params_and_run"}:
            if not targets:
                print("[WARN] Нет targets для set_params — пропуск применения параметров.")
            else:
                merged_values = merge_step_values(globals_map, step_params)
                for rel in targets:
                    target_path = (project_root / rel).resolve()
                    print(f"[INFO] Правим конфиг: {rel}")
                    if not target_path.exists():
                        print(f"[WARN] Файл не найден: {target_path}. Пропуск.")
                        if not continue_on_error:
                            print("[INFO] Остановлено из-за отсутствия файла и continue_on_error=false")
                            sys.exit(3)
                        continue

                    if dry_run:
                        _, stats = apply_params_to_file(target_path, merged_values, only_keys)
                        print(f"[DRY] changed={stats['changed']}, missing={stats['missing']}, skipped={stats['skipped']}")
                    else:
                        new_text, stats = apply_params_to_file(target_path, merged_values, only_keys)
                        print(f"[OK] changed={stats['changed']}")
                        if stats['missing']:
                            print(f"[WARN] missing={stats['missing']} (ключи не найдены — пропущены)")
                        if stats['skipped']:
                            print(f"[WARN] skipped={stats['skipped']} (неподдерживаемый тип значения)")
                        try:
                            atomic_write_text(target_path, new_text, backup=backup_configs)
                        except Exception as e:
                            print(f"[ERROR] Не удалось записать файл {target_path}: {e}")
                            if not continue_on_error:
                                sys.exit(4)

        if stype in {"run_script", "set_params_and_run"}:
            if not script_rel:
                print("[WARN] Скрипт не указан — пропуск запуска.")
            else:
                script_path = (project_root / script_rel).resolve()
                if not script_path.exists():
                    print(f"[ERROR] Скрипт не найден: {script_path}")
                    if not continue_on_error:
                        sys.exit(5)
                else:
                    if dry_run:
                        print(f"[DRY] Запустили бы: {python_exe} {script_path} {' '.join(script_args or [])}")
                    else:
                        code = run_script(python_exe, script_path, script_args, env=None)
                        if code != 0:
                            print(f"[ERROR] Скрипт вернул код {code}")
                            if not continue_on_error:
                                sys.exit(code)
                        else:
                            print("[OK] Скрипт завершился успешно.")

    print("\\n[INFO] Готово.")


if __name__ == "__main__":
    main()
