#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (shortened) — includes corrected to_toml_literal using TOML literal strings
import os, sys, re, subprocess, shutil
from pathlib import Path
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

def load_toml_bytes(p: Path) -> dict:
    with p.open('rb') as f:
        return tomllib.load(f)

def read_text(p: Path) -> str:
    return p.read_text(encoding='utf-8')

def atomic_write_text(p: Path, data: str, backup: bool):
    if backup and p.exists():
        bak = p.with_suffix(p.suffix + '.bak')
        try: shutil.copy2(p, bak)
        except Exception as e: print(f'[WARN] backup failed {bak}: {e}')
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(data, encoding='utf-8', newline='')
    os.replace(tmp, p)

def python_executable_from_options(options: dict) -> str:
    return (options or {}).get('python_executable', '') or sys.executable

def to_toml_literal(value):
    """Serialize basic types to TOML literals.
    Strings are emitted as *literal* strings with single quotes so backslashes
    are not escapes (ideal for Windows paths). If the string contains a single
    quote, fall back to a normal basic string with escapes.
    """
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        if "'" in value:
            v = value.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{v}"'
        else:
            return f"'{value}'"
    if isinstance(value, list):
        return '[' + ', '.join(to_toml_literal(x) for x in value) + ']'
    raise TypeError(f'Unsupported type for TOML: {type(value).__name__}')

def replace_key_in_toml_text(toml_text: str, key: str, new_value):
    pat = re.compile(rf'^(?P<prefix>\s*){re.escape(key)}\s*=\s*(?P<val>.+?)(?P<trail>\s*)(?P<comment>#.*)?$', re.MULTILINE)
    replaced = False
    def _repl(m):
        nonlocal replaced
        replaced = True
        prefix = m.group('prefix') or ''
        trail = m.group('trail') or ''
        comment = m.group('comment') or ''
        literal = to_toml_literal(new_value)
        return f"{prefix}{key} = {literal}{trail}{comment or ''}"
    new_text, _ = pat.subn(_repl, toml_text)
    return new_text, replaced

def apply_params_to_file(config_path: Path, values: dict, keys_order):
    text = read_text(config_path)
    stats = {'changed': [], 'missing': [], 'skipped': []}
    keys = list(values.keys()) if not keys_order else list(keys_order)
    for k in keys:
        if k not in values: continue
        v = values[k]
        try:
            new_text, ok = replace_key_in_toml_text(text, k, v)
        except TypeError:
            stats['skipped'].append(k); continue
        if ok: text = new_text; stats['changed'].append(k)
        else: stats['missing'].append(k)
    return text, stats

def merge_step_values_from_legacy(globals_map, step_params, only_keys):
    merged = dict(globals_map or {})
    if step_params: merged.update(step_params)
    if only_keys: merged = {k:v for k,v in merged.items() if k in only_keys}; order=list(only_keys)
    else: order = list(merged.keys())
    return merged, order

def resolve_params_block(globals_map: dict, step_params_list: list):
    values, order = {}, []
    for item in step_params_list or []:
        key = item.get('key')
        if not key: print("[WARN] [[steps.params]] missing 'key'"); continue
        use = (item.get('use') or 'global').strip().lower()
        if use not in {'global','value'}:
            print(f"[WARN] [[steps.params]] key={key}: bad use='{use}'"); continue
        if use == 'global':
            gk = item.get('global_key') or key
            if gk not in globals_map:
                print(f"[WARN] [[steps.params]] key={key}: global_key='{gk}' absent in [globals]"); continue
            values[key] = globals_map[gk]
        else:
            if 'value' not in item:
                print(f"[WARN] [[steps.params]] key={key}: use='value' but no 'value'"); continue
            values[key] = item['value']
        order.append(key)
    return values, order

def run_script(python_exe: str, script_path: Path, args, env):
    cmd = [python_exe, str(script_path)] + (args or [])
    print('[RUN]', ' '.join(cmd))
    try: return subprocess.run(cmd, env=env, cwd=str(script_path.parent)).returncode
    except FileNotFoundError as e:
        print(f'[ERROR] Launch failed {script_path}: {e}'); return 127

def main():
    root = Path(__file__).resolve().parent
    project_root = root.parent
    cfg_path = root / 'master_config.toml'
    if not cfg_path.exists():
        print('[ERROR] master_config.toml not found:', cfg_path, file=sys.stderr); sys.exit(2)

    data = load_toml_bytes(cfg_path)
    globals_map = data.get('globals', {}) or {}
    options = data.get('options', {}) or {}
    steps = data.get('steps', []) or []

    dry_run = bool(options.get('dry_run', False))
    continue_on_error = bool(options.get('continue_on_error', False))
    backup_configs = bool(options.get('backup_configs', True))
    python_exe = python_executable_from_options(options)

    print('[INFO] Start')
    print(f'[INFO] dry_run={dry_run} continue_on_error={continue_on_error} backup_configs={backup_configs}')
    print(f'[INFO] Python: {python_exe}')
    print(f'[INFO] Master dir: {root}')
    print(f'[INFO] Project root: {project_root}')

    for idx, step in enumerate(steps, 1):
        stype = (step.get('type') or '').strip()
        skip = bool(step.get('skip', False))
        halt_after = bool(step.get('halt_after', False))
        print(f"\n[STEP {idx}] type={stype} skip={skip} halt_after={halt_after}")

        if skip:
            print('[INFO] skipped by flag')
            if halt_after: print('[INFO] halt_after=true with skip — stopping'); break
            continue

        if stype not in {'set_params','run_script','set_params_and_run'}:
            print('[WARN] unknown step type, skipping'); continue

        targets = step.get('targets', []) or []
        explicit_params = step.get('params', []) or []
        only_keys = step.get('only_keys', None)
        legacy_step_params = step.get('step_params', None)

        script_rel = None; script_args = None
        if stype == 'run_script':
            script_rel = step.get('script'); script_args = step.get('args', [])
        elif stype == 'set_params_and_run':
            rb = step.get('run', {}) or {}
            script_rel = rb.get('script'); script_args = rb.get('args', [])

        if stype in {'set_params','set_params_and_run'}:
            if not targets:
                print('[WARN] no targets to apply'); 
            else:
                if explicit_params:
                    values, order = resolve_params_block(globals_map, explicit_params)
                else:
                    values, order = merge_step_values_from_legacy(globals_map, legacy_step_params, only_keys)
                if not values:
                    print('[WARN] nothing to change for this step')
                else:
                    for rel in targets:
                        tpath = (project_root / rel).resolve()
                        print('[INFO] edit:', rel)
                        if not tpath.exists():
                            print('[WARN] file not found:', tpath)
                            if not continue_on_error:
                                print('[INFO] stopping because continue_on_error=false'); sys.exit(3)
                            continue
                        if dry_run:
                            _, stats = apply_params_to_file(tpath, values, order)
                            print(f"[DRY] changed={stats['changed']} missing={stats['missing']} skipped={stats['skipped']}")
                        else:
                            new_text, stats = apply_params_to_file(tpath, values, order)
                            print(f"[OK] changed={stats['changed']}")
                            if stats['missing']: print(f"[WARN] missing={stats['missing']}")
                            if stats['skipped']: print(f"[WARN] skipped={stats['skipped']}")
                            try: atomic_write_text(tpath, new_text, backup=backup_configs)
                            except Exception as e:
                                print('[ERROR] write failed', tpath, e)
                                if not continue_on_error: sys.exit(4)

        if stype in {'run_script','set_params_and_run'}:
            if not script_rel: print('[WARN] no script in step')
            else:
                spath = (project_root / script_rel).resolve()
                if not spath.exists():
                    print('[ERROR] script not found:', spath)
                    if not continue_on_error: sys.exit(5)
                else:
                    if dry_run: print('[DRY] would run:', python_exe, spath, ' '.join(script_args or []))
                    else:
                        code = run_script(python_exe, spath, script_args, env=None)
                        if code != 0:
                            print('[ERROR] script exit code', code)
                            if not continue_on_error: sys.exit(code)
                        else:
                            print('[OK] script finished')

        if halt_after:
            print('[INFO] halt_after=true — stopping pipeline'); break

    print('\n[INFO] Done')


if __name__ == '__main__':
    main()
