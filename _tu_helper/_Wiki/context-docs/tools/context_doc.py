#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Docs Viewer — локальный просмотрщик документации из Markdown с расширенным поиском.
Один файл. Только стандартная библиотека. Python 3.8+.

ЗАЧЕМ НУЖЕН СКРИПТ
- Удобно хранить личную/командную доку в Markdown в Git-репозитории (папка docs).
- Быстро находить нужные разделы по ключу, алиасам, токенам и даже неточному запросу (fuzzy).
- Смотреть Markdown-текст, выбирать и копировать кодовые блоки, открывать исходный .md.

КАК ЭТО РАБОТАЕТ
- Рекурсивно сканируем ../docs (на один уровень выше скрипта).
- Парсим только .md (UTF-8, fallback cp1251), разбиваем на секции по заголовкам "## <ключ>".
- После заголовка допускаем строки:
    categories: Категория 1 - Подкатегория 2 - ...
    aliases: alias1, alias2; alias3 alias4
- Для каждой секции сохраняем:
    display_key, key (lowercase), tokens (разбиение по [^a-z0-9_]),
    categories[], aliases[], file_path, start_line, markdown, code_blocks[].
- В UI два дерева (Категории и Файлы), справа Markdown и кодовые блоки.
- Поддерживается история (Назад/Вперёд), автопоиск при запуске с аргументом.

СТРУКТУРА КОДА:
1) Импорты
2) Константы
3) Вспомогательные функции парсинга .md
4) Функции поиска (точный/алиасы/подстрока/токены/fuzzy)
5) Построение деревьев для UI (категории, файлы)
6) Утилиты (открыть файл в системе, буфер обмена, безопасное чтение)
7) Класс App_UI (весь UI + работа с уже подготовленными данными)
8) main()
9) if __name__ == '__main__': main()

Примечания:
- Код максимально линейный и "плоский": минимум вложенностей, подробные комментарии на русском
- Никаких внешних зависимостей, только стандартная библиотека
"""

# =========================
# 1) Импорты
# =========================
import os
import sys
import re
import difflib
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# =========================
# 2) Константы
# =========================
# Папка с документацией — по умолчанию на уровень выше скрипта
DEFAULT_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

# Папки, которые нужно игнорировать при рекурсивном сканировании
IGNORED_DIRS = {"node_modules", ".git", "site", ".venv", "venv", "__pycache__"}

# Регексы для парсинга
RE_SECTION_HEADER = re.compile(r"^\s*##\s+(?P<key>.+?)\s*$")  # строка заголовка секции
RE_OPTIONAL_SEPARATOR = re.compile(r"^\s*(=+|-+)\s*$")        # строки из ===== или -----
RE_CATEGORIES = re.compile(r"^\s*categories\s*:\s*(?P<cats>.+?)\s*$", re.IGNORECASE)
RE_ALIASES = re.compile(r"^\s*aliases\s*:\s*(?P<als>.+?)\s*$", re.IGNORECASE)
RE_CODE_FENCE_START = re.compile(r"^\s*```(?P<lang>[\w\+\-\#\.]+)?\s*$")  # ```lang
RE_CODE_FENCE_END = re.compile(r"^\s*```\s*$")
RE_TOKEN_SPLIT = re.compile(r"[^a-z0-9_]+")

# Символы для отображения в дереве файлов
ICON_FOLDER = "📁 "
ICON_FILE = "📄 "
SECTION_PREFIX = "§ "

# =========================
# 3) Вспомогательные функции парсинга .md
# =========================

def safe_read_text(path: Path) -> str:
    """
    Безопасное чтение текста:
    1) Сначала пробуем UTF-8
    2) Если не получилось — пробуем cp1251
    Возвращаем строку содержимого файла.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1251", errors="replace")


def normalize_key(s: str) -> str:
    """
    Нормализация ключей / алиасов для поиска:
    - Приводим к lowercase
    - Тримим пробелы
    """
    return (s or "").strip().lower()


def tokenize_key(key: str) -> List[str]:
    """
    Токенизация ключа для улучшенного поиска:
    - Разбиваем по любым символам кроме [a-z0-9_]
    - Фильтруем пустые
    Пример: "ul-ol-li" -> ["ul", "ol", "li"]
    """
    key_lc = normalize_key(key)
    parts = RE_TOKEN_SPLIT.split(key_lc)
    return [p for p in parts if p]


def parse_aliases(line_value: str) -> List[str]:
    """
    Разбор строки алиасов:
    - Алиасы могут быть разделены запятыми, точками с запятой или пробелами
    - Возвращаем список нормализованных (lowercase) алиасов
    """
    if not line_value:
        return []
    # Разделители: запятая, точка с запятой, пробелы
    raw = re.split(r"[,\;\s]+", line_value)
    return [normalize_key(x) for x in raw if x.strip()]


def parse_categories(line_value: str) -> List[str]:
    """
    Разбор строки категорий:
    - Формат: "Категория 1 - Категория 2 - ..."
    - Возвращаем список категорий без лишних пробелов (в исходном регистре для отображения)
    """
    if not line_value:
        return []
    parts = [p.strip() for p in line_value.split("-")]
    return [p for p in parts if p]


def extract_code_blocks(lines: List[str], start_index: int, end_index: int) -> List[Dict[str, str]]:
    """
    Извлекаем кодовые блоки в пределах секции.
    - Кодовые блоки ограничены тройными бэктиками ```...```
    - Поддерживаем любой язык (включая "c++", "tsx" и т.п.)
    - Возвращаем список словарей: {"lang": <язык или ''>, "code": <текст кода>}
    """
    blocks = []
    i = start_index
    in_code = False
    cur_lang = ""
    cur_lines = []

    while i < end_index:
        line = lines[i]

        if not in_code:
            # Проверяем начало блока кода: ```lang
            m = RE_CODE_FENCE_START.match(line)
            if m:
                in_code = True
                cur_lang = (m.group("lang") or "").strip()
                cur_lines = []
            # если не начало кода — просто идём дальше
        else:
            # Мы внутри кода — ищем конец ```
            if RE_CODE_FENCE_END.match(line):
                # Закрываем блок
                blocks.append({"lang": cur_lang, "code": "".join(cur_lines)})
                in_code = False
                cur_lang = ""
                cur_lines = []
            else:
                # Накапливаем строки кода
                cur_lines.append(line)

        i += 1

    return blocks


def parse_markdown_file(path: Path) -> List[Dict]:
    """
    Разбираем один .md файл и извлекаем список секций.
    Секция — это блок, который начинается с заголовка "## <ключ>".
    Сразу после заголовка допускаются опциональные строки:
      - разделители ===== / ----- (игнорируем, просто пропускаем)
      - categories: ...
      - aliases: ...
    Содержимое секции — всё до следующего заголовка "## " или конца файла.

    Возвращаем список словарей с полями:
      display_key, key, tokens, categories, aliases, file_path, start_line, markdown, code_blocks
    """
    text = safe_read_text(path)
    lines = text.splitlines(keepends=True)

    sections = []
    current_idx = 0
    n = len(lines)

    # Найдём все индексы строк, где начинается секция (## ...)
    header_positions = []
    for idx, line in enumerate(lines):
        if RE_SECTION_HEADER.match(line):
            header_positions.append(idx)

    # Для каждой позиции выделяем диапазон секции
    for si, start_line_idx in enumerate(header_positions):
        # Конец секции — либо следующий заголовок, либо конец файла
        end_line_idx = header_positions[si + 1] if si + 1 < len(header_positions) else n

        # Парсим заголовок
        header_match = RE_SECTION_HEADER.match(lines[start_line_idx])
        display_key = header_match.group("key").strip()
        key = normalize_key(display_key)
        tokens = tokenize_key(display_key)

        # После заголовка могут идти:
        # - строка ===== или -----
        # - categories: ...
        # - aliases: ...
        # Причём порядок может быть любым, но обычно — сперва разделитель
        i = start_line_idx + 1
        seen_categories = []
        seen_aliases = []

        # Движемся вниз, пропуская разделители и собирая categories/aliases
        while i < end_line_idx:
            s = lines[i]
            # Если это пустая строка — можно продолжать, но не обязательно
            if RE_OPTIONAL_SEPARATOR.match(s):
                i += 1
                continue

            mc = RE_CATEGORIES.match(s)
            if mc:
                seen_categories = parse_categories(mc.group("cats"))
                i += 1
                continue

            ma = RE_ALIASES.match(s)
            if ma:
                seen_aliases = parse_aliases(ma.group("als"))
                i += 1
                continue

            # Как только встретили строку, не подпадающую под эти кейсы — выходим
            break

        # markdown секции — это весь текст от строки i до end_line_idx
        md_text = "".join(lines[i:end_line_idx])

        # Вытащим кодовые блоки из всей секции
        code_blocks = extract_code_blocks(lines, i, end_line_idx)

        sections.append({
            "display_key": display_key,
            "key": key,
            "tokens": tokens,
            "categories": seen_categories,
            "aliases": seen_aliases,
            "file_path": str(path),
            "start_line": start_line_idx + 1,  # для удобства показываем 1-based
            "markdown": md_text,
            "code_blocks": code_blocks,
        })

    return sections


def scan_docs(root: Path) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
    """
    Рекурсивно сканируем папку root, игнорируя служебные директории.
    Для каждого .md файла парсим секции.
    Возвращаем:
      - flat_sections: плоский список всех секций
      - file_to_sections: словарь {путь_файла: [список секций этого файла]}
    """
    flat_sections: List[Dict] = []
    file_to_sections: Dict[str, List[Dict]] = {}

    for dirpath, dirnames, filenames in os.walk(root):
        # Фильтруем папки на месте (чтобы os.walk не заходил в них)
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            path = Path(dirpath) / name
            try:
                secs = parse_markdown_file(path)
                if secs:
                    flat_sections.extend(secs)
                    file_to_sections[str(path)] = secs
            except Exception as e:
                # Если какой-то файл не разобрался — просто сообщим в консоль и продолжим
                print(f"[WARN] Не удалось распарсить {path}: {e}", file=sys.stderr)

    return flat_sections, file_to_sections


# =========================
# 4) Функции поиска
# =========================

def build_search_index(sections: List[Dict]) -> Dict:
    """
    Готовим структуру для эффективного поиска:
    - keys -> список секций (ключи могут дублироваться в разных файлах)
    - alias_map -> alias -> список секций
    - flat списки для fuzzy (все ключи и все алиасы)
    """
    key_map: Dict[str, List[Dict]] = {}
    alias_map: Dict[str, List[Dict]] = {}
    all_keys = []
    all_aliases = []

    for s in sections:
        key_map.setdefault(s["key"], []).append(s)
        for a in s["aliases"]:
            alias_map.setdefault(a, []).append(s)

        if s["key"] not in all_keys:
            all_keys.append(s["key"])
        for a in s["aliases"]:
            if a not in all_aliases:
                all_aliases.append(a)

    return {
        "key_map": key_map,
        "alias_map": alias_map,
        "all_keys": all_keys,
        "all_aliases": all_aliases,
        "sections": sections,
    }


def search_sections(index: Dict, query: str) -> Tuple[Optional[Dict], List[Dict]]:
    """
    Главная логика поиска по приоритетам:
    1) Точное совпадение ключа (key == query)
    2) Точное совпадение по алиасу
    3) Подстрочное совпадение в key или алиасах
    4) Совпадение по токенам (хотя бы одно совпадение)
    5) Fuzzy-поиск (difflib) по ключам и алиасам

    Возвращаем (section_or_None, candidates_list).
    - Если найдено единственное точное совпадение — возвращаем его.
    - Если есть несколько кандидатов — возвращаем None и список кандидатов (UI предложит выбрать).
    - Если ничего не нашли — candidates может быть пустым.
    """
    q = normalize_key(query)
    if not q:
        return None, []

    key_map = index["key_map"]
    alias_map = index["alias_map"]
    all_sections = index["sections"]

    # 1) Точное совпадение ключа — приоритетнее всего
    if q in key_map:
        candidates = key_map[q]
        # Если одна секция — возвращаем её сразу, иначе отдаём список кандидатов
        if len(candidates) == 1:
            return candidates[0], candidates
        else:
            # точные совпадения идут первыми
            return None, candidates

    # 2) Точное совпадение по алиасу
    if q in alias_map:
        candidates = alias_map[q]
        if len(candidates) == 1:
            return candidates[0], candidates
        else:
            return None, candidates

    # 3) Подстрочное совпадение: ищем в key и алиасах
    sub_candidates: List[Dict] = []
    for s in all_sections:
        if q in s["key"]:
            sub_candidates.append(s)
            continue
        if any(q in a for a in s["aliases"]):
            sub_candidates.append(s)

    if sub_candidates:
        # Если ровно одна — вернём её, иначе список
        if len(sub_candidates) == 1:
            return sub_candidates[0], sub_candidates
        else:
            return None, sub_candidates

    # 4) Совпадение по токенам:
    q_tokens = tokenize_key(q)  # токены из запроса
    token_candidates = []
    if q_tokens:
        for s in all_sections:
            # если пересечение токенов непустое — считаем кандидатом
            if set(q_tokens) & set(s["tokens"]):
                token_candidates.append(s)

    if token_candidates:
        if len(token_candidates) == 1:
            return token_candidates[0], token_candidates
        else:
            return None, token_candidates

    # 5) Fuzzy — используем difflib.get_close_matches по ключам и по алиасам
    # Сначала пробуем среди ключей
    fuzzy_keys = difflib.get_close_matches(q, index["all_keys"], n=8, cutoff=0.6)
    fuzzy_aliases = difflib.get_close_matches(q, index["all_aliases"], n=8, cutoff=0.6)

    fuzzy_candidates: List[Dict] = []
    for fk in fuzzy_keys:
        fuzzy_candidates.extend(key_map.get(fk, []))
    for fa in fuzzy_aliases:
        fuzzy_candidates.extend(alias_map.get(fa, []))

    # Уберём дубли (одни и те же секции могли попасть несколько раз)
    seen = set()
    unique = []
    for s in fuzzy_candidates:
        nid = (s["file_path"], s["start_line"])
        if nid not in seen:
            seen.add(nid)
            unique.append(s)

    if unique:
        if len(unique) == 1:
            return unique[0], unique
        else:
            return None, unique

    # Ничего не нашли
    return None, []


# =========================
# 5) Построение деревьев для UI
# =========================

def build_category_tree(sections: List[Dict], docs_root: Path) -> Dict:
    """
    Строим структуру для дерева категорий:
    Возвращаем вложенный словарь вида:
    {
      "Категория 1": {
          "_children": { ... },
          "_sections": [ ... секции без подкатегорий ... ]
      },
      ...
    }
    И отдельный список секций без категорий — положим в корень "_sections".

    Внутри узлов категории "_sections" — список секций, реально отображаемых в дереве (как "§ ключ (rel_path)").
    """
    tree = {"_sections": []}

    for s in sections:
        cats = s["categories"]
        if not cats:
            tree["_sections"].append(s)
            continue

        # Идём по пути категорий
        node = tree
        for c in cats:
            if c not in node:
                node[c] = {"_sections": []}
            node = node[c]
        node["_sections"].append(s)

    return tree


def build_files_tree(docs_root: Path) -> Dict:
    """
    Строим простую структуру дерева файлов для UI:
    Возвращаем вложенную структуру:
    {
      "name": <имя папки>,
      "path": <абсолютный путь>,
      "dirs": [subtree...],
      "files": [ {"name": fname, "path": abspath}, ... ]
    }
    Только для директорий внутри docs_root, игнорируя служебные папки.
    """
    def walk_dir(path: Path) -> Dict:
        node = {
            "name": path.name,
            "path": str(path),
            "dirs": [],
            "files": []
        }
        try:
            for entry in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                if entry.is_dir():
                    if entry.name in IGNORED_DIRS:
                        continue
                    node["dirs"].append(walk_dir(entry))
                else:
                    if entry.name.lower().endswith(".md"):
                        node["files"].append({"name": entry.name, "path": str(entry)})
        except PermissionError:
            pass
        return node

    return walk_dir(docs_root)


# =========================
# 6) Утилиты
# =========================

def open_in_system(filepath: str):
    """
    Открыть файл штатной программой ОС.
    Кроссплатформенно:
      - Windows: os.startfile
      - macOS: open
      - Linux: xdg-open
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(filepath)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")


def ensure_sample_docs(docs_root: Path):
    """
    Если папка docs отсутствует — создадим.
    Если нет html.md и css.md — сгенерируем тестовые файлы с примерами:
    - минимум 2–3 секции
    - хотя бы одна секция с aliases
    - хотя бы один многоуровневый путь категорий
    - хотя бы один пример с несколькими кодовыми блоками
    """
    docs_root.mkdir(parents=True, exist_ok=True)

    html_path = docs_root / "html.md"
    css_path = docs_root / "css.md"

    if not html_path.exists():
        html_path.write_text("""---
## ul-ol-li
==========================
HTML - Списки
aliases: lists, bullets
Описание: Примеры неупорядоченных и упорядоченных списков в HTML.

```html
<ul>
  <li>HTML</li>
  <li>CSS</li>
  <li>JavaScript</li>
</ul>
