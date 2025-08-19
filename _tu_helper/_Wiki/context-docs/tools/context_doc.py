#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Docs Viewer — простой локальный просмотрщик документации из Markdown.

ОСОБЕННОСТИ:
- Папки с документациями перечисляются в файле doc_roots.txt (рядом со скриптом), по ОДНОЙ на строку.
  Пустые строки и строки, начинающиеся с '#', игнорируются. Пути можно указывать относительные (относительно doc_roots.txt).
  Если валидных путей нет — используем ../docs (относительно папки со скриптом).

- Формат .md (упрощённый, «терпимый»):
    ---
    # или ## (любой уровень)  <ключ>
    ==========================
    aliases: a1, a2, a3       (необязательно, можно где-то после заголовка)
    categories: A - B - C     (может быть несколько строк categories:)
    categories: X - Y
    (можно пустые/---/=== строки)
    <Произвольный markdown до следующего заголовка #...>

  Разделители (===/---) и пустые строки игнорируются парсером.
  Кодовые блоки в ```...``` извлекаются в список «сниппетов» (без тройных бэктиков).

- Поиск через Combobox (state="normal"):
  Подсказки обновляются на каждый ввод; порядок: Точное совпадение → Подстроки → Fuzzy.
  Пункт отображается как: "<ключ>    —    <имя_файла.md>".

- Дерево категорий:
  ОДНА и та же секция может появляться несколько раз (если categories: несколько).
  Для каждой вставки генерируется уникальный iid: "sec::<key>::<abs_path>::<instance>".

- Справа показывается: Markdown секции и ПУТЬ к файлу (под Markdown), ниже — список код-блоков и текст кода.

Зависимости: стандартная библиотека (tkinter, pathlib, re, difflib, webbrowser).
Python 3.8+
"""

from __future__ import annotations
import sys
import re
import difflib
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# --------------------------------------------------------------------
# ПУТИ/НАСТРОЙКИ
# --------------------------------------------------------------------

APP_TITLE = "Context Docs Viewer"

# Файл со списком корней документаций (рядом со скриптом)
DOC_ROOTS_FILE = Path(__file__).resolve().parent / "doc_roots.txt"
# Запасной путь (если файл не найден или пуст)
DEFAULT_FALLBACK_DOCS = (Path(__file__).resolve().parent.parent / "docs")

# Папки, которые не сканируем
IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}

# Регулярные выражения (простые и «терпимые»)
SEP_LINE_RE       = re.compile(r"^\s*[=\-]{3,}\s*$")          # строки из === или --- (любая длина, пробелы ок)
HEADER_RE         = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")     # заголовок секции: #, ##, ..., ###### + текст
ALIASES_RE        = re.compile(r"^\s*aliases\s*:\s*(.+)\s*$", re.I)     # aliases: a, b, c
CATEGORIES_RE     = re.compile(r"^\s*categories\s*:\s*(.+)\s*$", re.I)  # categories: A - B - C
FENCE_START_RE    = re.compile(r"^\s*```([^\s`]+)?\s*$")      # начало код-блока: ```lang (lang опционален)
FENCE_END_RE      = re.compile(r"^\s*```\s*$")                # конец код-блока: ```
TOKEN_SPLIT_RE    = re.compile(r"[^a-z0-9_]+")                # разбиение на токены для поиска


# --------------------------------------------------------------------
# МОДЕЛИ ДАННЫХ
# --------------------------------------------------------------------

@dataclass
class Section:
    """
    Одна секция документации.
    """
    key: str                         # нормализованный ключ (lower)
    display_key: str                 # «как написано» в заголовке (для показа)
    aliases: List[str]               # алиасы (lower)
    categories_list: List[List[str]] # список путей категорий (каждый путь = список уровней)
    markdown: str                    # ПОЛНЫЙ markdown ТЕКСТ секции (без строк aliases/categories)
    codes: List[str]                 # кодовые блоки (без тройных бэктиков)
    file_path: Path                  # исходный .md
    start_line: int                  # строка в файле (для отладки)


# --------------------------------------------------------------------
# ПОЛЕЗНЫЕ ФУНКЦИИ
# --------------------------------------------------------------------

def normalize_key(s: str) -> str:
    """Нормализация ключей/запросов: нижний регистр, обрезка пробелов."""
    return (s or "").strip().lower()

def tokenize(s: str) -> List[str]:
    """Разбить строку на токены по небуквенно-цифровым (кроме '_')."""
    s = normalize_key(s)
    return [t for t in TOKEN_SPLIT_RE.split(s) if t]

def is_sep_line(s: str) -> bool:
    """Является ли строка разделителем ===/--- (с учётом пробелов)."""
    return bool(SEP_LINE_RE.match(s or ""))


# --------------------------------------------------------------------
# ЧТЕНИЕ doc_roots.txt
# --------------------------------------------------------------------

def read_doc_roots() -> List[Path]:
    """
    Читает doc_roots.txt (рядом со скриптом) и возвращает список существующих папок.
    Если валидных путей нет — возвращает [../docs].
    """
    roots: List[Path] = []
    if DOC_ROOTS_FILE.exists():
        base = DOC_ROOTS_FILE.parent
        for raw in DOC_ROOTS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            if not p.is_absolute():
                p = (base / p).resolve()
            if p.exists() and p.is_dir():
                roots.append(p)
    if not roots:
        fb = DEFAULT_FALLBACK_DOCS.resolve()
        if fb.exists() and fb.is_dir():
            roots.append(fb)
    return roots


# --------------------------------------------------------------------
# ПАРСИНГ ОДНОГО .MD ФАЙЛА
# --------------------------------------------------------------------

def parse_md_file(md_path: Path) -> List[Section]:
    """
    Разбирает ОДИН .md на список Section.
    Логика:
      - Секция начинается с заголовка уровня 1..6: строка "# ...", "## ...", ..., "###### ..."
      - После заголовка читаем «мета»-строки: любые количества "aliases:" и "categories:" (в любом порядке),
        пропуская пустые/разделители.
      - Затем — произвольный Markdown до следующего заголовка.
      - В codes складываем содержимое ```...``` (без ограждений).
      - В markdown складываем контент БЕЗ строк aliases/categories (чтобы в тексте не дублировать).
    """
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    n = len(lines)
    sections: List[Section] = []

    # Ищем все заголовки 1..6 уровня
    headers = [i for i, line in enumerate(lines) if HEADER_RE.match(line)]
    if not headers:
        return sections
    headers.append(n)  # виртуальный конец

    for idx in range(len(headers) - 1):
        start = headers[idx]
        end   = headers[idx + 1]

        m = HEADER_RE.match(lines[start])
        if not m:
            continue

        display_key = m.group(1).strip()
        key = normalize_key(display_key)

        i = start + 1  # курсор на строку после заголовка

        # пропускаем пустые и разделители
        while i < end and (not lines[i].strip() or is_sep_line(lines[i])):
            i += 1

        # читаем мета-блок: aliases:/categories: (в любом порядке; categories может быть много раз)
        aliases: List[str] = []
        categories_list: List[List[str]] = []

        while i < end:
            s = lines[i].strip()
            if not s or is_sep_line(s):
                i += 1
                continue

            ma = ALIASES_RE.match(s)
            if ma:
                raw = ma.group(1)
                for a in re.split(r"[,\s;]+", raw):
                    a = normalize_key(a)
                    if a:
                        aliases.append(a)
                i += 1
                continue

            mc = CATEGORIES_RE.match(s)
            if mc:
                cat_line = mc.group(1).strip()
                if " - " in cat_line:
                    levels = [p.strip() for p in cat_line.split(" - ") if p.strip()]
                else:
                    levels = [cat_line] if cat_line else []
                if levels:
                    categories_list.append(levels)
                i += 1
                continue

            # попалась НЕ мета-строка — начинается контент
            break

        # контент секции от i до end
        content_lines = lines[i:end]

        # извлекаем кодовые блоки ```...``` (без ограждений)
        codes: List[str] = []
        in_code = False
        current: List[str] = []
        for line in content_lines:
            if not in_code and FENCE_START_RE.match(line):
                in_code = True
                current = []
                continue
            if in_code and FENCE_END_RE.match(line):
                codes.append("\n".join(current))
                in_code = False
                current = []
                continue
            if in_code:
                current.append(line)
        if in_code and current:
            codes.append("\n".join(current))  # на случай незакрытого блока

        markdown = "\n".join(content_lines).strip()

        sections.append(Section(
            key=key,
            display_key=display_key,
            aliases=aliases,
            categories_list=categories_list,
            markdown=markdown,
            codes=codes,
            file_path=md_path,
            start_line=start + 1
        ))

    return sections


# --------------------------------------------------------------------
# СБОР ВСЕХ ФАЙЛОВ/СЕКЦИЙ ИЗ КОРНЕЙ
# --------------------------------------------------------------------

def collect_sections_from_roots(roots: List[Path]) -> Tuple[List[Path], List[Section]]:
    """
    Идём по всем корневым папкам, собираем *.md (кроме IGNORE_DIRS), парсим секции.
    Возвращаем список файлов и список секций.
    """
    files: List[Path] = []
    sections: List[Section] = []
    for root in roots:
        for p in sorted(root.rglob("*.md")):
            # пропускаем нежелательные каталоги
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            files.append(p)
            sections.extend(parse_md_file(p))
    return files, sections


# --------------------------------------------------------------------
# ИНДЕКС/ПОИСК
# --------------------------------------------------------------------

class SearchIndex:
    """
    Индекс для поиска: ключи, алиасы, токены.
    """
    def __init__(self, sections: List[Section]):
        # ключ -> Section (если дубликаты — берём первый встретившийся)
        self.by_key: Dict[str, Section] = {}
        # алиас -> ключ
        self.alias_to_key: Dict[str, str] = {}
        # токен -> множество ключей
        self.token_to_keys: Dict[str, set] = {}
        # множество строк для fuzzy
        self.universe: set = set()

        for s in sections:
            if s.key not in self.by_key:
                self.by_key[s.key] = s
            self.universe.add(s.key)
            for t in tokenize(s.key):
                self.token_to_keys.setdefault(t, set()).add(s.key)
                self.universe.add(t)
            for a in s.aliases:
                self.alias_to_key[a] = s.key
                self.universe.add(a)
                for t in tokenize(a):
                    self.token_to_keys.setdefault(t, set()).add(s.key)
                    self.universe.add(t)

    def suggest(self, q: str, limit: int = 50) -> List[str]:
        """
        Подсказки (список КЛЮЧЕЙ) для Combobox.
        Порядок: точные → подстроки (ключи, алиасы, токены) → fuzzy. Уникальные. До limit.
        """
        q = normalize_key(q)
        results: List[str] = []

        if not q:
            # без запроса — просто отсортированный список ключей (но ограничим)
            return sorted(self.by_key.keys())[:limit]

        # 1) точное
        if q in self.by_key:
            results.append(q)

        # 2) подстроки по ключам
        subs_keys = [k for k in self.by_key if q in k and k not in results]
        subs_keys.sort(key=lambda k: (k.find(q), len(k)))
        results.extend(subs_keys)

        # 3) подстроки по алиасам
        alias_hits = [self.alias_to_key[a] for a in self.alias_to_key if q in a]
        for k in alias_hits:
            if k not in results:
                results.append(k)

        # 4) подстроки по токенам
        for t, keys in self.token_to_keys.items():
            if q in t:
                for k in keys:
                    if k not in results:
                        results.append(k)

        # 5) fuzzy
        if len(results) < limit:
            near = difflib.get_close_matches(q, list(self.universe), n=limit, cutoff=0.7)
            for s in near:
                if s in self.by_key and s not in results:
                    results.append(s)
                elif s in self.alias_to_key:
                    k = self.alias_to_key[s]
                    if k not in results:
                        results.append(k)
                elif s in self.token_to_keys:
                    for k in self.token_to_keys[s]:
                        if k not in results:
                            results.append(k)

        return results[:limit]

    def find_best(self, q: str) -> Optional[Section]:
        """Лучшая секция под запрос: точное совпадение → первая из suggest()."""
        q = normalize_key(q)
        if not q:
            return None
        if q in self.by_key:
            return self.by_key[q]
        sug = self.suggest(q, limit=1)
        if sug:
            return self.by_key.get(sug[0])
        return None


# --------------------------------------------------------------------
# ДЕРЕВО КАТЕГОРИЙ (вставка секций)
# --------------------------------------------------------------------

def add_section_to_tree(tree: ttk.Treeview, root_id: str, cat_path: List[str],
                        section: Section, instance_number: int) -> None:
    """
    Вставляет секцию по пути категорий (cat_path).
    Генерирует УНИКАЛЬНЫЙ iid для §-узла:
      "sec::<key>::<abs_path>::<instance_number>"
    """
    parent = root_id

    # Проходим по уровням категорий и создаём узлы, если их ещё нет
    for level in cat_path:
        # Ищем среди детей узел с таким же «text»
        found = None
        for child in tree.get_children(parent):
            if tree.item(child, "text") == level:
                found = child
                break
        if found is None:
            found = tree.insert(parent, "end", text=level, open=False)
        parent = found

    # Лист — сама секция
    unique_iid = f"sec::{section.key}::{section.file_path.resolve()}::{instance_number}"
    tree.insert(parent, "end", iid=unique_iid, text=f"§ {section.key}")


# --------------------------------------------------------------------
# ПРИЛОЖЕНИЕ (Tkinter)
# --------------------------------------------------------------------

class App:
    def __init__(self, root: tk.Tk, initial_query: str = ""):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1150x780")
        root.minsize(900, 600)

        # 1) читаем корни и собираем секции
        self.doc_roots = read_doc_roots()
        self.all_files, self.sections = collect_sections_from_roots(self.doc_roots)

        # Диагностика для удобства (видно, что именно нашлось)
        if not self.all_files:
            messagebox.showwarning(
                "Файлы не найдены",
                "Не найдено ни одного .md файла в следующих корнях:\n\n"
                + "\n".join(str(p) for p in self.doc_roots)
            )
        elif not self.sections:
            messagebox.showwarning(
                "Секции не найдены",
                f"Найдено .md файлов: {len(self.all_files)}, но секций не распознано.\n\n"
                "Проверьте, что заголовки разделов начинаются с '#' или '##' (например, '# ul-ol-li')."
            )

        # 2) индекс для поиска
        self.index = SearchIndex(self.sections)

        # Текущее состояние
        self.current_section: Optional[Section] = None

        # 3) UI
        self._build_topbar()
        self._build_body()
        self._fill_categories_tree()

        # 4) если передан стартовый запрос — подставим и откроем
        if initial_query:
            self.search_combo.set(initial_query)
            self.open_best_from_combo()

    # ---------------- 顶няя панель (поиск) ----------------
    def _build_topbar(self) -> None:
        top = ttk.Frame(self.root, padding=6)
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Поиск по ключу:").pack(side=tk.LEFT, padx=(0, 6))

        self.search_combo = ttk.Combobox(top, state="normal", values=[], width=42)
        self.search_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # обновлять список кандидатов при наборе
        self.search_combo.bind("<KeyRelease>", self._on_query_changed)
        # Enter — открыть лучшую секцию
        self.search_combo.bind("<Return>", lambda e: self.open_best_from_combo())

        ttk.Button(top, text="Открыть", command=self.open_best_from_combo).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Найти в дереве", command=self.locate_in_tree).pack(side=tk.LEFT)

    # ---------------- Тело окна ----------------
    def _build_body(self) -> None:
        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        # Слева — дерево категорий
        left = ttk.Frame(body)
        body.add(left, weight=1)

        self.cat_tree = ttk.Treeview(left, show="tree")
        self.cat_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.cat_tree.bind("<Double-1>", self._on_tree_activate)
        self.cat_tree.bind("<Return>", self._on_tree_activate)

        # Справа — верх: Markdown + путь к файлу; низ — код
        right = ttk.Panedwindow(body, orient=tk.VERTICAL)
        body.add(right, weight=3)

        # Верх: Markdown
        md_wrap = ttk.Frame(right, padding=6)
        right.add(md_wrap, weight=3)

        self.md_text = ScrolledText(md_wrap, wrap="word")
        self.md_text.pack(fill=tk.BOTH, expand=True)
        self.md_text.configure(state="disabled")

        # Путь к файлу (под Markdown)
        path_bar = ttk.Frame(md_wrap)
        path_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(path_bar, text="Файл:").pack(side=tk.LEFT)
        self.path_value = ttk.Entry(path_bar, state="readonly")
        self.path_value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        # Низ: кодовые блоки
        low = ttk.Frame(right, padding=6)
        right.add(low, weight=2)

        row = ttk.Frame(low)
        row.pack(fill=tk.X)
        ttk.Label(row, text="Кодовые блоки:").pack(side=tk.LEFT)
        self.code_combo = ttk.Combobox(row, state="readonly", values=[])
        self.code_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
        self.code_combo.bind("<<ComboboxSelected>>", lambda e: self._update_code_view())

        btns = ttk.Frame(low)
        btns.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btns, text="Скопировать весь блок", command=self.copy_whole_section).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Скопировать код", command=self.copy_code).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Открыть .md", command=self.open_md_file).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Закрыть", command=self.root.destroy).pack(side=tk.RIGHT, padx=4)

        self.code_text = ScrolledText(low, wrap="none", height=12)
        self.code_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.code_text.configure(state="disabled")

    # ---------------- Заполнение дерева категорий ----------------
    def _fill_categories_tree(self) -> None:
        self.cat_tree.delete(*self.cat_tree.get_children())

        # счётчик вхождений для уникальных iid
        per_file_counter: Dict[str, int] = {}

        for s in self.sections:
            paths = s.categories_list or [["Без категории"]]
            for cat_path in paths:
                key = str(s.file_path.resolve())
                per_file_counter[key] = per_file_counter.get(key, 0) + 1
                add_section_to_tree(self.cat_tree, "", cat_path, s, per_file_counter[key])

    # ---------------- Обновление подсказок поиска ----------------
    def _on_query_changed(self, event=None) -> None:
        q = self.search_combo.get().strip()
        keys = self.index.suggest(q, limit=50)

        # точное совпадение — в начало (перестраховка; suggest уже так делает)
        exact = normalize_key(q)
        if exact in keys:
            ordered = [exact] + [k for k in keys if k != exact]
        else:
            ordered = keys

        # Собираем «человеческие» подписи
        out = []
        for k in ordered:
            sec = self.index.by_key.get(k)
            if not sec:
                continue
            out.append(f"{k}    —    {sec.file_path.name}")

        self.search_combo["values"] = out

    def _extract_key_from_combo(self) -> str:
        """
        Возвращает ключ из Combobox:
          - если выбран из списка "key — file.md" — берём левую часть;
          - если введён вручную — берём как есть.
        """
        raw = self.search_combo.get().strip()
        parts = raw.split("—")
        if len(parts) >= 2:
            return parts[0].strip()
        return raw

    def open_best_from_combo(self) -> None:
        q = self._extract_key_from_combo()
        if not q:
            messagebox.showinfo("Поиск", "Введите ключ для поиска.")
            return
        sec = self.index.find_best(q)
        if not sec:
            messagebox.showinfo("Поиск", f"Ничего не найдено для: {q}")
            return
        self.open_section(sec)

    # ---------------- Открытие секции ----------------
    def _on_tree_activate(self, event=None) -> None:
        item = self.cat_tree.focus()
        if not item:
            return
        text = self.cat_tree.item(item, "text")
        if not text.startswith("§ "):
            return
        key = text[2:].strip()
        sec = self.index.by_key.get(key)
        if sec:
            self.open_section(sec)

    def open_section(self, sec: Section) -> None:
        self.current_section = sec

        # Markdown (заголовок и тело; служебные строки не вставляем)
        header = f"# {sec.display_key}"
        self.md_text.configure(state="normal")
        self.md_text.delete("1.0", "end")
        self.md_text.insert("1.0", header + "\n\n")
        if sec.markdown:
            self.md_text.insert("end", sec.markdown)
        self.md_text.configure(state="disabled")

        # Путь к файлу
        try:
            self.path_value.configure(state="normal")
            self.path_value.delete(0, "end")
            self.path_value.insert(0, str(sec.file_path.resolve()))
        finally:
            self.path_value.configure(state="readonly")

        # Код-блоки
        if sec.codes:
            items = [f"Блок #{i+1} — {len(c.splitlines())} строк" for i, c in enumerate(sec.codes)]
            self.code_combo["values"] = items
            self.code_combo.current(0)
        else:
            self.code_combo["values"] = ["— нет кода —"]
            self.code_combo.current(0)
        self._update_code_view()

    # ---------------- Работа с кодом ----------------
    def _update_code_view(self) -> None:
        self.code_text.configure(state="normal")
        self.code_text.delete("1.0", "end")
        if self.current_section and self.current_section.codes:
            idx = self.code_combo.current()
            if idx is None or idx < 0:
                idx = 0
            if 0 <= idx < len(self.current_section.codes):
                self.code_text.insert("1.0", self.current_section.codes[idx])
        self.code_text.configure(state="disabled")

    def copy_whole_section(self) -> None:
        if not self.current_section:
            return
        text = f"# {self.current_section.display_key}\n\n{self.current_section.markdown}"
        self._to_clipboard(text)

    def copy_code(self) -> None:
        if not self.current_section or not self.current_section.codes:
            return
        idx = self.code_combo.current()
        if idx is None or idx < 0:
            idx = 0
        if 0 <= idx < len(self.current_section.codes):
            self._to_clipboard(self.current_section.codes[idx])

    def _to_clipboard(self, text: str) -> None:
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text or "")
        except Exception as e:
            messagebox.showerror("Копирование", f"Не удалось скопировать:\n{e}")

    def open_md_file(self) -> None:
        if not self.current_section:
            return
        webbrowser.open(self.current_section.file_path.resolve().as_uri())

    # ---------------- Позиционирование в дереве ----------------
    def locate_in_tree(self) -> None:
        if not self.current_section:
            messagebox.showinfo("Навигация", "Сначала откройте секцию.")
            return
        target = f"§ {self.current_section.key}"

        def expand_parents(iid: str):
            parent = self.cat_tree.parent(iid)
            while parent:
                self.cat_tree.item(parent, open=True)
                parent = self.cat_tree.parent(parent)

        def walk(parent="") -> bool:
            for child in self.cat_tree.get_children(parent):
                if self.cat_tree.item(child, "text") == target:
                    expand_parents(child)
                    self.cat_tree.see(child)
                    self.cat_tree.selection_set(child)
                    self.cat_tree.focus(child)
                    return True
                if walk(child):
                    return True
            return False

        walk("")


# --------------------------------------------------------------------
# ТОЧКА ВХОДА
# --------------------------------------------------------------------

def main():
    initial = sys.argv[1] if len(sys.argv) > 1 else ""
    root = tk.Tk()
    app = App(root, initial_query=initial)
    root.mainloop()

if __name__ == "__main__":
    main()
