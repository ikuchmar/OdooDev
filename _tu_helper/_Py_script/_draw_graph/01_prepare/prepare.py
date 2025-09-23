#!/usr/bin/env python3
# 01_prepare / prepare.py (final updated, outs header fix)
# ... (docstring omitted for brevity; same as previous, but outs dump uses multiline form)

from __future__ import annotations
import sys, re, fnmatch, unicodedata
import tomllib
from pathlib import Path

def read_toml_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")

def load_config(cfg_path: Path) -> dict:
    raw = read_toml_text(cfg_path)
    return tomllib.loads(raw)

def norm_key(k: str) -> str:
    return re.sub(r'[\s_\-]+', '', k or '').lower()

def build_alias_maps(cfg: dict):
    aliases = cfg.get("aliases", {})
    fields = aliases.get("fields", {})
    fam_blocks = aliases.get("blocks", [])
    canon_blocks = [norm_key(x) for x in fam_blocks] or ['blocks','block','node','узел','блок','блоки']
    field_map = {}
    for canon, alist in fields.items():
        for a in alist:
            field_map[norm_key(a)] = canon
        field_map[norm_key(canon)] = canon
    return set(canon_blocks), field_map

CYR_MAP = {
    'а':'a','б':'b','в':'v','г':'g','ґ':'g','д':'d','е':'e','ё':'e','є':'ie','ж':'zh',
    'з':'z','и':'i','і':'i','ї':'i','й':'i','к':'k','л':'l','м':'m','н':'n','о':'o',
    'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh',
    'щ':'sch','ы':'y','э':'e','ю':'yu','я':'ya','ь':'','ъ':'','’':'','ʼ':''
}
def slugify(s: str, maxlen=40) -> str:
    if not isinstance(s, str): s = str(s)
    s = s.strip().lower()
    out = []
    for ch in s:
        if ch in CYR_MAP: out.append(CYR_MAP[ch]); continue
        if ch.isalnum() or ch in ['_', '-', '.', '/']:
            out.append(ch)
        elif ch.isspace() or ch in [':','|']:
            out.append('-')
    res = ''.join(out)
    res = re.sub(r'-{2,}', '-', res).strip('-_.')
    return res[:maxlen] or 'block'

def title_from_id(id_or_name: str) -> str:
    return str(id_or_name).replace('_',' ').replace('-',' ').title()

SAFE_TOKEN_RE = re.compile(r'^[A-Za-z0-9_.\-/]+(?::[A-Za-z0-9_.\-/]+)?$')

def preprocess_text(txt: str, cfg: dict, fam_blocks, field_map, notes_out):
    keep_original = cfg.get("behavior", {}).get("keep_original", False)
    lines = txt.splitlines()
    out_lines = []
    appendix = []

    def is_block_header(name: str) -> bool:
        return norm_key(name) in fam_blocks

    def replace_key_aliases(key: str) -> str:
        nk = norm_key(key)
        return field_map.get(nk, key)

    i = 0
    while i < len(lines):
        line = lines[i]
        m_hdr2 = re.match(r'^\s*\[\[\s*([^\]]+?)\s*\]\]\s*(#.*)?$', line)
        m_hdr1 = re.match(r'^\s*\[\s*([^\]]+?)\s*\]\s*(#.*)?$', line)
        if m_hdr2 or m_hdr1:
            name = (m_hdr2 or m_hdr1).group(1).strip()
            if is_block_header(name):
                if keep_original == "inline":
                    out_lines.append(f"# [prepare] header: [{name}] → [[blocks]]")
                elif keep_original == "appendix":
                    appendix.append(f"# [prepare] header: [{name}] → [[blocks]]")
                    appendix.append(f"#   {line}")
                out_lines.append("[[blocks]]")
                i += 1
                continue
            else:
                out_lines.append(line); i += 1; continue

        m_kv = re.match(r'^(\s*)([^=\s]+)\s*=\s*(.*)$', line)
        if m_kv:
            indent, key_raw, value_raw = m_kv.group(1), m_kv.group(2), m_kv.group(3)
            nk = norm_key(key_raw)
            if nk in fam_blocks:
                value = value_raw.strip()
                if value.startswith('"""') and not value.endswith('"""'):
                    collected = [value]; i += 1
                    while i < len(lines):
                        collected.append(lines[i])
                        if lines[i].rstrip().endswith('"""'): break
                        i += 1
                    value = '\n'.join(collected)
                expanded, report = expand_block_shorthand(value)
                if expanded is None:
                    out_lines.append(f"# [prepare] cannot parse: {line}")
                    notes_out.append("expand.block: skipped invalid line")
                else:
                    for b in expanded:
                        if keep_original == "inline":
                            out_lines.append(f"# [prepare] expand.block: {key_raw} = {b['__src']}")
                        elif keep_original == "appendix":
                            appendix.append(f"# [prepare] expand.block: {key_raw} = {b['__src']}")
                        out_lines.append("[[blocks]]")
                        out_lines.append(f'id = "{b["id"]}"')
                        out_lines.append(f'title = "{b["title"]}"')
                        if b["props"]:
                            props_join = ", ".join([f'"{p}"' for p in b["props"]])
                            out_lines.append(f'properties = [{props_join}]')
                        else:
                            out_lines.append('properties = []')
                i += 1
                continue

            canon_key = replace_key_aliases(key_raw)
            key_changed = (canon_key != key_raw)
            if canon_key in ("id","title"):
                v = value_raw.strip()
                if not (v.startswith('"') or v.startswith("'")) and SAFE_TOKEN_RE.match(v):
                    value_raw = f'"{v}"'
                    notes_out.append(f'autofix.{canon_key}: quoted {v}')
                    if keep_original == "inline":
                        out_lines.append(f'# [prepare] quoted: {canon_key} = {v} → "{v}"')
                    elif keep_original == "appendix":
                        appendix.append(f'# [prepare] quoted: {canon_key} = {v} → "{v}"')

            if canon_key == "outs":
                tmp = fix_array_simple_tokens(value_raw)
                if tmp != value_raw:
                    if keep_original == "inline":
                        out_lines.append("# [prepare] quoted tokens in outs")
                    elif keep_original == "appendix":
                        appendix.append(f"# [prepare] quoted tokens in outs: {value_raw.strip()}")
                    value_raw = tmp

            if canon_key == "properties":
                tmp = fix_array_simple_tokens(value_raw, allow_scalar=True)
                if tmp != value_raw:
                    if keep_original == "inline":
                        out_lines.append("# [prepare] normalized properties tokens")
                    elif keep_original == "appendix":
                        appendix.append(f"# [prepare] normalized properties tokens: {value_raw.strip()}")
                    value_raw = tmp

            if key_changed:
                if keep_original == "inline":
                    out_lines.append(f"# [prepare] alias: {key_raw} → {canon_key}")
                elif keep_original == "appendix":
                    appendix.append(f"# [prepare] alias: {key_raw} → {canon_key}")
            out_lines.append(f"{indent}{canon_key} = {value_raw}")
            i += 1
            continue

        out_lines.append(line); i += 1

    if keep_original == "appendix" and appendix:
        out_lines.append("")
        out_lines.append("# [prepare] Appendix: original fragments")
        out_lines.extend(appendix)
    return "\n".join(out_lines) + "\n"

def expand_block_shorthand(value: str):
    src = value.strip()
    items = []
    if src.startswith('"""') and src.endswith('"""'):
        body = src[3:-3]
        lines = [ln.strip() for ln in body.splitlines()]
        for ln in lines:
            if not ln: continue
            item = parse_block_line(ln)
            if item is None: return None, "bad line"
            items.append(item | {"__src": ln})
        return items, "ok"
    else:
        line = src.strip()
        if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
            line = line[1:-1]
        item = parse_block_line(line)
        if item is None: return None, "bad line"
        return [item | {"__src": line}], "ok"

def parse_block_line(line: str):
    parts = [p.strip() for p in re.split(r'\s*,\s*', line) if p.strip() != ""]
    if not parts: return None
    def unq(s: str) -> str:
        return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'") else s
    parts = [unq(p) for p in parts]
    first = parts[0]
    if re.match(r'^[A-Za-z0-9_.\-/]+$', first):
        bid = first
        if len(parts) == 1:
            title = title_from_id(bid); props = []
        elif len(parts) == 2:
            title = parts[1]; props = []
        else:
            title = parts[1]; props = parts[2:]
        return {"id": bid, "title": title, "props": props}
    else:
        title = first
        bid = slugify(title)
        props = parts[1:] if len(parts) > 1 else []
        return {"id": bid, "title": title, "props": props}

def fix_array_simple_tokens(vraw: str, allow_scalar=False) -> str:
    v = vraw.strip()
    if allow_scalar and not v.startswith('['):
        base = v.strip()
        if not (base.startswith('"') or base.startswith("'")) and re.match(r'^[A-Za-z0-9_.\-/:]+$', base):
            return f'["{base}"]'
        return vraw
    if not v.startswith('['): return vraw
    content = vraw
    res = []; token = ""; in_s = False; quote = ''
    for ch in content:
        if in_s:
            token += ch
            if ch == quote: in_s = False
            continue
        if ch in ('"', "'"):
            in_s = True; quote = ch; token += ch; continue
        if ch == ',':
            res.append(token); token = ""
        else:
            token += ch
    if token: res.append(token)
    fixed_chunks = []
    for chunk in res:
        if '#' in chunk:
            body, comment = chunk.split('#', 1)
            suffix = '#' + comment
        else:
            body, suffix = chunk, ''
        body_strip = body.strip()
        m = re.match(r'^(.*?)([A-Za-z0-9_.\-/]+(?::[A-Za-z0-9_.\-/]+)?)(\s*[\]\s]*)$', body_strip)
        if m and not ('"' in body_strip or "'" in body_strip):
            prefix, tok, rest = m.groups()
            body_strip = f'{prefix}"{tok}"{rest}'
        fixed = body_strip
        if suffix: fixed += ' ' + suffix.strip()
        fixed_chunks.append(' ' + fixed)
    return ','.join(fixed_chunks)

def parse_outs_value(v):
    pairs = []
    if isinstance(v, str):
        items = [x.strip() for x in v.split(',') if x.strip()]
        for x in items:
            to, label = (x.split(':', 1) + [""])[:2]
            pairs.append((to.strip(), label.strip()))
    elif isinstance(v, list):
        for x in v:
            if isinstance(x, str):
                to, label = (x.split(':', 1) + [""])[:2]
                pairs.append((to.strip(), label.strip()))
    return [(a, b) for a, b in pairs if a]

def ensure_unique_ids(blocks, notes):
    seen = {}
    for idx, b in enumerate(blocks):
        bid = b.get("id") or ""
        if not bid:
            base = slugify(b.get("title") or f"block-{idx+1}")
            bid = base
            notes.append(f'block#{idx+1}: added id={bid}')
        base = bid; k = base; n = 1
        while k in seen:
            n += 1; k = f"{base}__{n:02d}"
        if k != bid:
            notes.append(f'block#{idx+1}: id conflict, renamed {bid} → {k}')
        b["id"] = k; seen[k] = True

def normalize_blocks(graph, notes):
    blocks = graph.get("blocks") or []
    normed = []
    for idx, b in enumerate(blocks, start=1):
        nb = {}
        for k in ["id","name","title","pos","width","header_height","prop_height","properties","outs"]:
            if k in b: nb[k] = b[k]
        if not nb.get("title"):
            if nb.get("name"):
                nb["title"] = str(nb["name"]); notes.append(f'block#{idx}: added title from name')
            elif nb.get("id"):
                nb["title"] = title_from_id(nb["id"]); notes.append(f'block#{idx}: added title from id')
        if "properties" not in nb or nb.get("properties") is None:
            nb["properties"] = []; notes.append(f'block#{idx}: added properties=[]')
        else:
            if isinstance(nb["properties"], str):
                nb["properties"] = [x.strip() for x in nb["properties"].split(',') if x.strip()]
            elif isinstance(nb["properties"], list):
                nb["properties"] = [str(x) for x in nb["properties"]]
            else:
                nb["properties"] = [str(nb["properties"])]
        outs = []
        if "outs" in nb:
            outs = parse_outs_value(nb["outs"])
        seen = set(); out_list = []
        for to, label in outs:
            key = (to, label)
            if key in seen:
                notes.append(f'dedup.out: ({to}|{label})')
                continue
            seen.add(key); out_list.append({"to": to, "label": label})
        nb["outs"] = out_list
        normed.append(nb)
    ensure_unique_ids(normed, notes)
    return normed

def q(s): return '"' + str(s).replace('\\', '\\\\').replace('"','\\"') + '"'

def _toml_val(v):
    if isinstance(v, str): return q(v)
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, list): return '[' + ', '.join(_toml_val(x) for x in v) + ']'
    return q(str(v))

def dump_graph(graph: dict, notes: list[str]):
    out = []
    meta = graph.get("meta", {})
    pn = list(meta.get("prepare_notes", []))
    pn.extend(notes)
    seen = set(); pn2 = []
    for n in pn:
        if n in seen: continue
        seen.add(n); pn2.append(n)
    meta["prepare_notes"] = pn2
    if meta:
        out.append("[meta]")
        for k, v in meta.items():
            out.append(f"{k} = {_toml_val(v)}")
        out.append("")
    for b in graph.get("blocks", []):
        out.append("")
        out.append("[[blocks]]")
        for k in ["id","name","title","pos","width","header_height","prop_height"]:
            if k in b and b[k] not in (None, "", []):
                out.append(f"{k} = {_toml_val(b[k])}")
        props = b.get("properties", [])
        if props is None: props = []
        out.append("properties = " + _toml_val([str(x) for x in props]))
        for o in b.get("outs", []):
            to = o.get("to",""); label = o.get("label","")
            out.append("[[blocks.outs]]")
            out.append(f"to = {q(to)}")
            out.append(f"label = {q(label)}")
        out.append("")
    out.append("")
    return "\n".join(out).lstrip("\n")

def discover_files(io_cfg: dict):
    input_dirs = io_cfg.get("input_dirs", [])
    recursive = io_cfg.get("recursive", True)
    exclude_patterns = [p.lower() for p in io_cfg.get("exclude_patterns", [])]
    input_suffix = io_cfg.get("input_suffix", ".toml").lower()
    files = []
    for d in input_dirs:
        base = Path(d)
        if not base.exists(): continue
        it = base.rglob("*") if recursive else base.glob("*")
        for p in it:
            if not p.is_file(): continue
            low = p.name.lower()
            if not low.endswith(input_suffix): continue
            if any(fnmatch.fnmatch(low, pat) for pat in exclude_patterns): continue
            files.append(p)
    return files

def main():
    root = Path(__file__).parent
    cfg_path = root / "config_prepare.toml"
    cfg = load_config(cfg_path)

    fam_blocks, field_map = build_alias_maps(cfg)
    io_cfg = cfg.get("io", {})
    beh = cfg.get("behavior", {})
    keep_original = beh.get("keep_original", False)
    output_suffix = io_cfg.get("output_suffix", "_01")

    files = discover_files(io_cfg)
    print(f"[prepare] Found: {len(files)} file(s)")

    for src in files:
        if src.name.lower().endswith((output_suffix + ".toml").lower()):
            print(f"[skip] {src.name} already suffixed"); continue

        notes = []
        try:
            txt = read_toml_text(src)
            pre_txt = preprocess_text(txt, cfg, fam_blocks, field_map, notes)
            out_path = src.with_name(src.stem + output_suffix + src.suffix)
            out_path.write_text(pre_txt, encoding="utf-8")

            try:
                graph = tomllib.loads(pre_txt)
            except Exception as e:
                banner = f"# [prepare] parse_error: {e.__class__.__name__}: {e}\n"
                out_path.write_text(banner + pre_txt, encoding="utf-8")
                print(f"[parse-error] {src.name} → {out_path.name}")
                continue

            graph["blocks"] = normalize_blocks(graph, notes)
            final_txt = dump_graph(graph, notes)
            out_path.write_text(final_txt, encoding="utf-8")
            print(f"[ok] {src.name} → {out_path.name}")
        except Exception as e:
            print(f"[ERR] {src}: {e}")
            continue

if __name__ == "__main__":
    main()
