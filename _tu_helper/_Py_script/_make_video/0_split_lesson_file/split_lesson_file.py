# -*- coding: utf-8 -*-
r"""
Скрипт: режет учебные тексты на СЕКЦИИ и извлекает БЛОКИ (EN/RU/и любые другие из config.toml).
Сохраняет каждый блок в отдельный файл с суффиксом. Работает и с нумерованными, и с ненумерованными заголовками.

Особенности:
 - INPUT.input_dirs — список папок с исходниками
 - OUTPUT.output_root — если пусто, файлы пишутся рядом с исходником
 - BLOCKS.rules — список правил для блоков (markers, suffix, sentence_per_line, remove_empty_lines)
 - [ADVANCED].delete_source_after = true → удалить исходный файл после успешной генерации

Config: config.toml
"""

import os
import re
import sys
from typing import List, Dict, Tuple, Optional

# tomllib для Python 3.11+, иначе tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

SECTION_HEADER_NUM_RE = re.compile(
    r'^[ \t]*([0-9]+)\.([0-9]+)[ \t]+(.+?)\s*$',
    re.UNICODE
)
INVALID_FILENAME_CHARS = r'\/:*?"<>|'


def normalize_path(p: Optional[str]) -> Optional[str]:
    if p is None:
        return None
    p = str(p).strip()
    if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
        p = p[1:-1].strip()
    return os.path.normpath(p)


def sanitize_filename(name: str) -> str:
    trans = {ord(ch): ' ' for ch in INVALID_FILENAME_CHARS}
    cleaned = name.translate(trans)
    return re.sub(r'\s+', ' ', cleaned, flags=re.UNICODE).strip()


def pad_number(n: int, width: int) -> str:
    return str(n).zfill(width)


def load_config(path: str = "config.toml") -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Не найден {path}.")
    with open(path, "rb") as f:
        data = tomllib.load(f)

    input_dirs = [normalize_path(p) for p in data.get("INPUT", {}).get("input_dirs", [])]
    if not input_dirs:
        raise ValueError("В config.toml не задан INPUT.input_dirs.")
    extensions = [str(e).lower() for e in data.get("INPUT", {}).get("extensions", [".txt"])]
    recursive = bool(data.get("INPUT", {}).get("recursive", True))

    output_root = normalize_path(data.get("OUTPUT", {}).get("output_root", None)) or None
    naming = data.get("NAMING", {})
    pad_chapter = bool(naming.get("pad_chapter_to_3", True))
    pad_section = bool(naming.get("pad_section_to_2", True))
    title_sep = str(naming.get("title_separator", " "))
    extension = str(naming.get("extension", ".txt"))
    if not extension.startswith("."):
        extension = "." + extension
    base_chapter = int(naming.get("base_chapter", 0))

    adv = data.get("ADVANCED", {})
    ignore_hidden = bool(adv.get("ignore_hidden", True))
    skip_empty = bool(adv.get("skip_files_without_sections", True))
    source_encoding = str(adv.get("source_encoding", "utf-8"))
    output_encoding = str(adv.get("output_encoding", "utf-8"))
    delete_source_after = bool(adv.get("delete_source_after", False))

    blocks_cfg = data.get("BLOCKS", {}).get("rules", [])
    blocks: List[dict] = []
    for b in blocks_cfg:
        name = str(b.get("name", "")).strip()
        if not name:
            continue
        blocks.append({
            "name": name,
            "markers": [str(m) for m in b.get("markers", [])],
            "suffix": str(b.get("suffix", "")).strip(),
            "sentence_per_line": bool(b.get("sentence_per_line", False)),
            "remove_empty_lines": bool(b.get("remove_empty_lines", False)),
        })

    return {
        "input_dirs": input_dirs,
        "extensions": extensions,
        "recursive": recursive,
        "output_root": output_root,
        "pad_chapter": pad_chapter,
        "pad_section": pad_section,
        "title_sep": title_sep,
        "extension": extension,
        "base_chapter": base_chapter,
        "ignore_hidden": ignore_hidden,
        "skip_empty": skip_empty,
        "source_encoding": source_encoding,
        "output_encoding": output_encoding,
        "delete_source_after": delete_source_after,
        "blocks": blocks,
    }


def read_text(path: str, encoding: str) -> str:
    with open(path, "r", encoding=encoding, newline="") as f:
        text = f.read()
    return text.lstrip("\ufeff").lstrip("\uFEFF").lstrip("\u200b")


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def iter_files(root: str, extensions: List[str], recursive: bool, ignore_hidden: bool) -> List[str]:
    res = []
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return res
    if not recursive:
        for fn in os.listdir(root):
            full = os.path.join(root, fn)
            if os.path.isfile(full) and os.path.splitext(fn)[1].lower() in extensions:
                if not (ignore_hidden and fn.startswith(".")):
                    res.append(full)
        return res
    for dirpath, dirnames, filenames in os.walk(root):
        if ignore_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if ignore_hidden and fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() in extensions:
                res.append(os.path.join(dirpath, fn))
    return res


def sanitize_block_text(text: str) -> str:
    lines = text.splitlines()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    out = []
    prev_empty = False
    for ln in lines:
        is_empty = (ln.strip() == "")
        if is_empty and prev_empty:
            continue
        out.append(ln)
        prev_empty = is_empty
    if len(out) >= 2 and out[1].strip() != "":
        out.insert(1, "")
    return "\n".join(out) + ("\n" if out else "")


def split_sections(text: str, base_chapter: int) -> List[Dict]:
    lines = text.splitlines()
    sections = []
    current, buf, found_num = None, [], False
    for line in lines:
        m = SECTION_HEADER_NUM_RE.match(line)
        if m:
            found_num = True
            if current is not None:
                current["body"] = sanitize_block_text("\n".join(buf))
                sections.append(current)
                buf = []
            current = {"chapter": int(m.group(1)), "section": int(m.group(2)), "title": m.group(3), "body": ""}
            buf.append(line)
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        current["body"] = sanitize_block_text("\n".join(buf))
        sections.append(current)
    return sections


def extract_blocks_from_section(section_text: str, blocks_cfg: List[dict]) -> Dict[str, str]:
    lines = section_text.splitlines()
    found = []
    for b in blocks_cfg:
        for m in b["markers"]:
            for i, ln in enumerate(lines):
                if ln.strip().startswith(m):
                    found.append((i, b["name"]))
    found.sort(key=lambda x: x[0])
    first_idx = {}
    ordered = []
    for idx, name in found:
        if name not in first_idx:
            first_idx[name] = idx
            ordered.append((idx, name))
    result = {}
    for k, (idx, name) in enumerate(ordered):
        start, end = idx + 1, len(lines)
        if k + 1 < len(ordered):
            end = ordered[k + 1][0]
        body = "\n".join(lines[start:end])
        result[name] = sanitize_block_text(body)
    return result


def split_into_sentences(text: str) -> List[str]:
    one_line = re.sub(r'[ \t]*\n[ \t]*', ' ', text.strip())
    return [p.strip() for p in re.split(r'(?<=[\.\?\!])\s+', one_line) if p.strip()]


def format_block_text(raw_text: str, sentence_per_line: bool, remove_empty_lines: bool) -> str:
    lines = raw_text.splitlines()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    tmp, prev_empty = [], False
    for ln in lines:
        is_empty = (ln.strip() == "")
        if is_empty and prev_empty:
            continue
        tmp.append(ln)
        prev_empty = is_empty
    lines = tmp
    if not lines:
        return ""
    if remove_empty_lines:
        lines = [ln for ln in lines if ln.strip() != ""]
    if not sentence_per_line:
        return "\n".join(lines) + "\n"
    first = lines[0].rstrip()
    has_punct = bool(re.search(r'[\.!\?:]\s*$', first))
    is_title = (not has_punct) and (len(first) <= 120)
    if is_title:
        title = first
        rest = "\n".join(lines[1:]).strip()
        sentences = split_into_sentences(rest) if rest else []
        out = [title, ""] if title else []
        out.extend(sentences)
        return "\n".join(out) + ("\n" if out else "")
    else:
        sentences = split_into_sentences("\n".join(lines))
        return "\n".join(sentences) + ("\n" if sentences else "")


def build_base_filename(ch: int, sec: int, title: str, pad_ch: bool, pad_sec: bool, sep: str) -> str:
    return f"{pad_number(ch,3) if pad_ch else ch}_{pad_number(sec,2) if pad_sec else sec}{sep}{sanitize_filename(title)}"


def write_block_files(base_name: str, out_dir: str, ext: str, blocks_text: Dict[str, str],
                      blocks_cfg: List[dict], output_encoding: str) -> List[str]:
    ensure_dir(out_dir)
    created = []
    for b in blocks_cfg:
        text = blocks_text.get(b["name"], "")
        if not text.strip():
            continue
        text = format_block_text(text, b["sentence_per_line"], b["remove_empty_lines"])
        if not text.strip():
            continue
        fname = f"{base_name}{b['suffix']}{ext}"
        full_path = os.path.join(out_dir, fname)
        with open(full_path, "w", encoding=output_encoding, newline="\n") as f:
            f.write(text)
        created.append(full_path)
    return created


def process_file(src_file: str, cfg: dict, rel_root: Optional[str] = None) -> List[str]:
    text = read_text(src_file, cfg["source_encoding"])
    sections = split_sections(text, cfg["base_chapter"])
    if not sections and cfg["skip_empty"]:
        return []
    created_all = []
    for s in sections:
        base_name = build_base_filename(s["chapter"], s["section"], s["title"],
                                        cfg["pad_chapter"], cfg["pad_section"], cfg["title_sep"])
        if cfg["output_root"]:
            src_abs, root_abs = os.path.abspath(src_file), os.path.abspath(rel_root) if rel_root else os.path.dirname(src_file)
            rel_dir = os.path.relpath(os.path.dirname(src_abs), root_abs)
            if rel_dir == ".":
                rel_dir = ""
            out_dir = os.path.join(cfg["output_root"], rel_dir)
        else:
            out_dir = os.path.dirname(src_file)
        blocks_text = extract_blocks_from_section(s["body"], cfg["blocks"])
        created = write_block_files(base_name, out_dir, cfg["extension"], blocks_text, cfg["blocks"], cfg["output_encoding"])
        created_all.extend(created)
    if created_all and cfg["delete_source_after"]:
        try:
            os.remove(src_file)
            print(f"[INFO] Удалён исходный файл: {src_file}")
        except Exception as e:
            print(f"[WARN] Не удалось удалить {src_file}: {e}")
    return created_all


def main():
    cfg = load_config("config.toml")
    print("INPUT DIRS:", *cfg["input_dirs"], sep="\n  - ")
    print("OUTPUT ROOT:", cfg["output_root"] or "(рядом с исходником)")
    print("BLOCKS:", [b["name"] for b in cfg["blocks"]])
    created_total = []
    for src_root in cfg["input_dirs"]:
        files = iter_files(src_root, cfg["extensions"], cfg["recursive"], cfg["ignore_hidden"])
        for f in files:
            created_total += process_file(f, cfg, rel_root=src_root)
    print("Готово. Создано файлов:", len(created_total))


if __name__ == "__main__":
    main()
