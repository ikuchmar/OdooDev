# -*- coding: utf-8 -*-
r"""
Режет учебные тексты на СЕКЦИИ и извлекает БЛОКИ (EN/RU/словари и т.п.) по config.toml.
Работает с нумерованными заголовками N.N Title. (Эвристика ненумерованных при желании можно вернуть.)

Новые вещи:
 - Робастное распознавание маркеров блоков: трим BOM/ZWSP/NBSP, игнорируем ведущие пробелы,
   поддерживаем case-insensitive (опция в блоке).
 - Подробные логи: показываем, сколько файлов/секций/блоков найдено и что записано.
 - Остальное: запись рядом с исходником, если OUTPUT.output_root не задан; delete_source_after.

Config: config.toml
"""

import os
import re
from typing import List, Dict, Tuple, Optional

# tomllib для Python 3.11+, иначе tomli
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

SECTION_HEADER_NUM_RE = re.compile(r'^[ \t]*([0-9]+)\.([0-9]+)[ \t]+(.+?)\s*$', re.UNICODE)
INVALID_FILENAME_CHARS = r'\/:*?"<>|'  # Windows имя


# -------------------------------
# Утилиты: пути/строки/логи
# -------------------------------
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


def log(msg: str):
    print(msg, flush=True)


# -------------------------------
# Загрузка конфига
# -------------------------------
def load_config(path: str = "config.toml") -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Не найден {path}.")
    with open(path, "rb") as f:
        data = tomllib.load(f)

    # INPUT
    input_dirs = [normalize_path(p) for p in data.get("INPUT", {}).get("input_dirs", []) if str(p).strip()]
    if not input_dirs:
        raise ValueError("В config.toml не задан INPUT.input_dirs.")
    extensions = [str(e).lower() for e in data.get("INPUT", {}).get("extensions", [".txt"])]
    recursive = bool(data.get("INPUT", {}).get("recursive", True))

    # OUTPUT
    output_root = normalize_path(data.get("OUTPUT", {}).get("output_root", None)) or None

    # NAMING
    naming = data.get("NAMING", {})
    pad_chapter = bool(naming.get("pad_chapter_to_3", True))
    pad_section = bool(naming.get("pad_section_to_2", True))
    title_sep = str(naming.get("title_separator", " "))
    extension = str(naming.get("extension", ".txt"))
    if not extension.startswith("."):
        extension = "." + extension
    base_chapter = int(naming.get("base_chapter", 0))  # для ненумерованных (если вернёте эвристику)

    # ADVANCED
    adv = data.get("ADVANCED", {})
    ignore_hidden = bool(adv.get("ignore_hidden", True))
    skip_empty = bool(adv.get("skip_files_without_sections", True))
    source_encoding = str(adv.get("source_encoding", "utf-8"))
    output_encoding = str(adv.get("output_encoding", "utf-8"))
    delete_source_after = bool(adv.get("delete_source_after", False))

    # BLOCKS
    blocks_cfg_in = data.get("BLOCKS", {}).get("rules", [])
    blocks: List[dict] = []
    for b in blocks_cfg_in:
        name = str(b.get("name", "")).strip()
        if not name:
            continue
        blocks.append({
            "name": name,
            "markers": [str(m) for m in b.get("markers", []) if str(m).strip()],
            "suffix": str(b.get("suffix", "")).strip(),
            "sentence_per_line": bool(b.get("sentence_per_line", False)),
            "remove_empty_lines": bool(b.get("remove_empty_lines", False)),
            # новая опция: регистр маркеров
            "ignore_case": bool(b.get("ignore_case", True)),
            # новая опция: игнорировать пробелы перед маркером
            "ignore_leading_space": bool(b.get("ignore_leading_space", True)),
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


# -------------------------------
# IO
# -------------------------------
def read_text(path: str, encoding: str) -> str:
    with open(path, "r", encoding=encoding, newline="") as f:
        text = f.read()
    # Убираем BOM/ZWSP с начала
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
            if not os.path.isfile(full):
                continue
            if ignore_hidden and fn.startswith("."):
                continue
            if os.path.splitext(fn)[1].lower() in extensions:
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


# -------------------------------
# Санитизация секции
# -------------------------------
def sanitize_block_text(text: str) -> str:
    lines = text.splitlines()
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    out, prev_empty = [], False
    for ln in lines:
        is_empty = (ln.strip() == "")
        if is_empty and prev_empty:
            continue
        out.append(ln)
        prev_empty = is_empty
    if len(out) >= 2 and out[1].strip() != "":
        out.insert(1, "")
    return "\n".join(out) + ("\n" if out else "")


# -------------------------------
# Парсинг секций (нумерованные)
# -------------------------------
def split_sections(text: str) -> List[Dict]:
    lines = text.splitlines()
    sections, current, buf = [], None, []

    for line in lines:
        m = SECTION_HEADER_NUM_RE.match(line)
        if m:
            if current is not None:
                current["body"] = sanitize_block_text("\n".join(buf))
                sections.append(current)
                buf = []
            current = {
                "chapter": int(m.group(1)),
                "section": int(m.group(2)),
                "title": m.group(3),
                "body": ""
            }
            buf.append(line)
        else:
            if current is not None:
                buf.append(line)

    if current is not None:
        current["body"] = sanitize_block_text("\n".join(buf))
        sections.append(current)
    return sections


# -------------------------------
# Извлечение БЛОКОВ
# -------------------------------
NBSP = "\u00A0"
ZWSP = "\u200B"
BOMS = ("\ufeff", "\uFEFF")

def _strip_invisibles(s: str) -> str:
    # убираем BOM/ZWSP/NBSP в начале строки и ведущие пробелы/табы
    s = s.lstrip(" \t" + NBSP + "".join(BOMS) + ZWSP)
    return s

def _norm_for_compare(s: str, ignore_case: bool) -> str:
    s = _strip_invisibles(s)
    return s.lower() if ignore_case else s

def extract_blocks_from_section(section_text: str, blocks_cfg: List[dict], verbose: bool=False) -> Dict[str, str]:
    """
    Ищем строки, начинающиеся с любого из заданных маркеров (с учётом опций ignore_case/ignore_leading_space).
    Контент блока — от строки-маркера (исключая её) до следующего маркера/конца секции.
    """
    lines = section_text.splitlines()
    found: List[Tuple[int, str, str]] = []

    # индексация маркеров
    for b in blocks_cfg:
        name = b["name"]
        ignore_case = b.get("ignore_case", True)
        for raw_marker in b["markers"]:
            marker_cmp = raw_marker.lower() if ignore_case else raw_marker
            for i, ln in enumerate(lines):
                cmp_line = _norm_for_compare(ln, ignore_case)
                if cmp_line.startswith(marker_cmp):
                    found.append((i, name, raw_marker))

    if verbose:
        if found:
            log("    [debug] найденные маркеры: " + ", ".join([f"{n}@{i}" for i, n, _ in sorted(found)]))
        else:
            log("    [debug] маркеры не найдены в этой секции")

    if not found:
        return {}

    found.sort(key=lambda x: x[0])

    first_marker_idx: Dict[str, int] = {}
    ordered: List[Tuple[int, str, str]] = []
    for idx, name, raw_marker in found:
        if name not in first_marker_idx:
            first_marker_idx[name] = idx
            ordered.append((idx, name, raw_marker))
    ordered.sort(key=lambda x: x[0])

    result: Dict[str, str] = {}
    for k, (idx, name, _) in enumerate(ordered):
        start_line = idx + 1
        end_line = len(lines)
        if k + 1 < len(ordered):
            end_line = ordered[k + 1][0]
        body_lines = lines[start_line:end_line]
        body = "\n".join(body_lines)
        result[name] = sanitize_block_text(body)
    return result


# -------------------------------
# Форматирование блока
# -------------------------------
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


# -------------------------------
# Запись
# -------------------------------
def build_base_filename(ch: int, sec: int, title: str, pad_ch: bool, pad_sec: bool, sep: str) -> str:
    ch_str = pad_number(ch, 3) if pad_ch else str(ch)
    sec_str = pad_number(sec, 2) if pad_sec else str(sec)
    return f"{ch_str}_{sec_str}{sep}{sanitize_filename(title)}"

def write_block_files(base_name: str, out_dir: str, ext: str, blocks_text: Dict[str, str],
                      blocks_cfg: List[dict], output_encoding: str) -> List[str]:
    ensure_dir(out_dir)
    created = []
    for b in blocks_cfg:
        name = b["name"]
        suffix = b["suffix"]
        text = blocks_text.get(name, "")
        if not text.strip():
            log(f"      [skip] блок '{name}' пуст — пропущен")
            continue
        text = format_block_text(text, b["sentence_per_line"], b["remove_empty_lines"])
        if not text.strip():
            log(f"      [skip] блок '{name}' стал пустым после форматирования — пропущен")
            continue
        fname = f"{base_name}{suffix}{ext}"
        full_path = os.path.join(out_dir, fname)
        with open(full_path, "w", encoding=output_encoding, newline="\n") as f:
            f.write(text)
        created.append(full_path)
        log(f"      [ok]   записано: {fname}")
    return created


# -------------------------------
# Главный цикл по файлам
# -------------------------------
def process_file(src_file: str, cfg: dict, rel_root: Optional[str] = None) -> List[str]:
    log(f"[file] {src_file}")
    text = read_text(src_file, cfg["source_encoding"])
    sections = split_sections(text)
    log(f"   найдено секций: {len(sections)}")

    if not sections and cfg["skip_empty"]:
        log("   [warn] секций нет — пропуск файла")
        return []

    created_all: List[str] = []
    for s in sections:
        base_name = build_base_filename(
            s["chapter"], s["section"], s["title"],
            cfg["pad_chapter"], cfg["pad_section"], cfg["title_sep"]
        )
        # Куда писать
        if cfg["output_root"]:
            src_abs = os.path.abspath(src_file)
            root_abs = os.path.abspath(rel_root) if rel_root else os.path.dirname(src_abs)
            rel_dir = os.path.relpath(os.path.dirname(src_abs), root_abs)
            if rel_dir == ".":
                rel_dir = ""
            out_dir = os.path.join(cfg["output_root"], rel_dir)
        else:
            out_dir = os.path.dirname(src_file)

        log(f"    секция: {s['chapter']}.{s['section']} — {s['title']}")
        blocks_text = extract_blocks_from_section(s["body"], cfg["blocks"], verbose=True)
        if not blocks_text:
            log("    [warn] маркеры блоков не найдены — секция пропущена")
            continue

        created = write_block_files(base_name, out_dir, cfg["extension"], blocks_text, cfg["blocks"], cfg["output_encoding"])
        created_all.extend(created)

    if created_all and cfg["delete_source_after"]:
        try:
            os.remove(src_file)
            log(f"   [info] удалён исходный файл: {src_file}")
        except Exception as e:
            log(f"   [warn] не удалось удалить {src_file}: {e}")

    return created_all


def main():
    cfg = load_config("config.toml")

    log("INPUT DIRS:")
    for d in cfg["input_dirs"]:
        log(f"  - {d}")
    log(f"OUTPUT ROOT: {cfg['output_root'] or '(рядом с исходником)'}")
    log("BLOCKS: " + ", ".join([b["name"] for b in cfg["blocks"]]))

    created_total: List[str] = []
    total_files = 0

    for src_root in cfg["input_dirs"]:
        files = []
        if os.path.isdir(src_root):
            # итерация по файлам
            def _iter(root):
                root = os.path.abspath(root)
                if not cfg["recursive"]:
                    for fn in os.listdir(root):
                        full = os.path.join(root, fn)
                        if os.path.isfile(full) and os.path.splitext(fn)[1].lower() in cfg["extensions"]:
                            if not (cfg["ignore_hidden"] and fn.startswith(".")):
                                files.append(full)
                else:
                    for dirpath, dirnames, filenames in os.walk(root):
                        if cfg["ignore_hidden"]:
                            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                        for fn in filenames:
                            if cfg["ignore_hidden"] and fn.startswith("."):
                                continue
                            if os.path.splitext(fn)[1].lower() in cfg["extensions"]:
                                files.append(os.path.join(dirpath, fn))
            _iter(src_root)
        elif os.path.isfile(src_root) and os.path.splitext(src_root)[1].lower() in cfg["extensions"]:
            files = [src_root]
        else:
            log(f"[warn] пропуск несуществующего пути: {src_root}")
            continue

        files.sort()
        total_files += len(files)
        log(f"[scan] найдено файлов в «{src_root}»: {len(files)}")

        for f in files:
            created_total += process_file(f, cfg, rel_root=src_root)

    log(f"Готово. Создано файлов: {len(created_total)} из {total_files} исходных.")
    if not created_total:
        log("Подсказка: проверьте в config.toml раздел BLOCKS.rules → markers (точное написание),\n"
            "а также что ваши файлы действительно содержат строки-маркеры (например, «EN:», «RU:», «Новые слова:»).")


if __name__ == "__main__":
    main()
