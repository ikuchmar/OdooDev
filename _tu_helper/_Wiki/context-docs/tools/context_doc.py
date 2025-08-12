#!/usr/bin/env python3
"""
open_doc.py — простой просмотрщик локальной документации из Markdown
для запуска из PyCharm (External Tool). Показывает секции по ключу
и позволяет навигироваться по категориям/файлам, копировать кодовые блоки.

Зависимости: только стандартная библиотека (tkinter, pathlib, difflib, re, webbrowser).
Python 3.8+
"""

from __future__ import annotations

import sys
import re
import difflib
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# -----------------------------------------------------------------------------
# ПУТИ И НАСТРОЙКИ
# -----------------------------------------------------------------------------

# Корень с документацией (папка docs/ на один уровень выше tools/)
DOCS_ROOT = Path(__file__).parent.parent / "docs"

# Папки, которые не нужно обходить рекурсивно
IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}

# Разделитель категорий в строке после "## ключ"
CATEGORY_SEP = " - "

# Регулярки:
#   - Разделительная линия (=== или --- любой длины, пробелы допустимы)
SEP_LINE_RE = re.compile(r"^\s*[=\-]{3,}\s*$")
#   - Начало/конец ограждения кодового блока (``` что угодно)
FENCE_RE = re.compile(r"^\s*```")


# -----------------------------------------------------------------------------
# ДАННЫЕ
# -----------------------------------------------------------------------------

@dataclass
class Section:
    """
    Одна секция документации.
    key         — ключ для поиска (в нижнем регистре)
    categories  — строка категорий "A - B - C" (может быть пустой)
    markdown    — полный markdown секции (включая строку '## ключ', но без строки категорий)
    codes       — список кодовых блоков (без тройных бэктиков)
    file_path   — путь к исходному .md
    """
    key: str
    categories: str
    markdown: str
    codes: List[str]
    file_path: Path


# -----------------------------------------------------------------------------
# ПАРСИНГ MARKDOWN
# -----------------------------------------------------------------------------

def parse_md_file(md_path: Path) -> List[Section]:
    """
    Разбирает один .md-файл на секции.
    Формат секции:

      (опц) =======
      ## ключ
      (опц) =======
      (опц) пустые строки
      (опц) Кат1 - Кат2 - КатN
      (опц) -------
      далее произвольный markdown до следующего '## '
      код-блоки в ```…``` (язык внутри не обязателен)

    ВАЖНО:
      - Разделители ===/--- игнорируются парсером.
      - Строка категорий — первая непустая и не-разделительная строка после заголовка.
      - В full-markdown включаем и заголовок, и ограждения ```...```.
      - В codes записываем ЧИСТЫЙ текст изнутри код-блоков (без ограждений).

    Возвращает список Section.
    """
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    sections: List[Section] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Ищем заголовок секции
        if line.startswith("## "):
            key_display = line[3:].strip()  # как показано в файле
            key = key_display.lower()  # ключ для поиска (lower)
            i += 1

            # Пропускаем пустые и разделительные строки
            while i < n and (not lines[i].strip() or SEP_LINE_RE.match(lines[i])):
                i += 1

            # Читаем строку категорий (если она есть и это не разделитель/новая секция)
            categories = ""
            if i < n and not lines[i].startswith("## ") and not SEP_LINE_RE.match(lines[i]):
                categories = lines[i].strip()
                i += 1

            # Пропустим возможный разделитель/пустые строки сразу после категорий
            while i < n and (not lines[i].strip() or SEP_LINE_RE.match(lines[i])):
                i += 1

            # Теперь читаем контент секции до следующего "## "
            # В markdown добавляем СНАЧАЛА строку заголовка
            content_lines: List[str] = [f"## {key_display}"]
            codes: List[str] = []
            current_code: Optional[List[str]] = None

            while i < n and not lines[i].startswith("## "):
                cur = lines[i]

                if FENCE_RE.match(cur):
                    # Ограждение всегда попадает в markdown
                    content_lines.append(cur)

                    if current_code is None:
                        # Начали код-блок
                        current_code = []
                    else:
                        # Закрыли код-блок — сохраним чистый текст
                        codes.append("\n".join(current_code))
                        current_code = None

                    i += 1
                    continue

                # Строка идёт в markdown
                content_lines.append(cur)

                # Если внутри кода — копим его без бэктиков
                if current_code is not None:
                    current_code.append(cur)

                i += 1

            # Если код-блок не закрыли — всё равно сохраним накопленное
            if current_code is not None:
                codes.append("\n".join(current_code))

            markdown = "\n".join(content_lines).strip()
            sections.append(Section(key=key,
                                    categories=categories,
                                    markdown=markdown,
                                    codes=codes,
                                    file_path=md_path))
        else:
            i += 1

    return sections


def load_all_sections(root: Path) -> List[Section]:
    """
    Рекурсивно собирает секции из всех .md в папке root, игнорируя системные каталоги.
    """
    all_sections: List[Section] = []
    for path in root.rglob("*.md"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        all_sections.extend(parse_md_file(path))
    return all_sections


# -----------------------------------------------------------------------------
# ПОСТРОЕНИЕ ДЕРЕВЬЕВ (КАТЕГОРИИ / ФАЙЛЫ)
# -----------------------------------------------------------------------------

def build_categories_index(sections: List[Section]) -> Dict:
    """
    Готовит дерево категорий вида:
      { "Cat": { "Sub": { "__sections__": [Section, ...] } } }
    Пустые уровни НЕ создаются.
    """
    tree: Dict = {}
    for s in sections:
        parts = [p.strip() for p in s.categories.split(CATEGORY_SEP) if p.strip()]
        node = tree
        for p in parts:
            node = node.setdefault(p, {})
        node.setdefault("__sections__", []).append(s)
    return tree


def build_files_index(sections: List[Section]) -> Dict:
    """
    Готовит дерево по файловой структуре:
      { "dir": { "subdir": { "file.md": [Section, ...] } } }
    """
    tree: Dict = {}
    for s in sections:
        rel = s.file_path.relative_to(DOCS_ROOT)
        parts = list(rel.parts)
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault(parts[-1], []).append(s)
    return tree


# -----------------------------------------------------------------------------
# UI — ПОМОЩНИКИ
# -----------------------------------------------------------------------------

def make_section_iid(sec: Section) -> str:
    """Уникальный идентификатор узла секции в деревьях (чтобы к нему можно было фокусироваться)."""
    return f"sec::{sec.key}::{sec.file_path}"


def tree_expand_parents(tree: ttk.Treeview, iid: str) -> None:
    """Разворачивает всех родителей узла."""
    parent = tree.parent(iid)
    while parent:
        tree.item(parent, open=True)
        parent = tree.parent(parent)


def tree_find_and_focus(tree: ttk.Treeview, target_iid: str) -> bool:
    """Ищет узел с target_iid и фокусирует его (с разворачиванием родителей)."""

    def walk(parent="") -> bool:
        for child in tree.get_children(parent):
            if child == target_iid:
                tree_expand_parents(tree, child)
                tree.selection_set(child)
                tree.focus(child)
                tree.see(child)
                return True
            if walk(child):
                return True
        return False

    return walk("")


# -----------------------------------------------------------------------------
# ПРИЛОЖЕНИЕ
# -----------------------------------------------------------------------------

class App:
    """
    Главное окно приложения.
    Содержит:
      - верхняя панель: поиск + история + кнопки
      - слева: вкладки "Категории" и "Файлы"
      - справа: 2 блока — верхний markdown и нижний код с Combobox
    """

    def __init__(self, root: tk.Tk, sections: List[Section], initial_term: str):
        self.root = root
        self.sections = sections
        self.initial_term = initial_term.strip()

        # Индексы для быстрого доступа
        self.flat_by_key: Dict[str, List[Section]] = self._group_by_key(sections)
        self.cats_index = build_categories_index(sections)
        self.files_index = build_files_index(sections)

        # Текущее состояние
        self.current: Optional[Section] = None
        self.history: List[Section] = []
        self.hist_idx: int = -1

        # Элементы UI (инициализируются в build_ui)
        self.search_var: tk.StringVar
        self.search_entry: tk.Entry
        self.btn_back: tk.Button
        self.btn_fwd: tk.Button
        self.tree_cats: ttk.Treeview
        self.tree_files: ttk.Treeview
        self.markdown_view: ScrolledText
        self.code_combo: ttk.Combobox
        self.code_view: ScrolledText

        self.build_ui()

        # Предзаполнение поиска и авто-поиск при старте
        if self.initial_term:
            self.search_var.set(self.initial_term)
            self.do_search()

    # --- индексы ---

    @staticmethod
    def _group_by_key(sections: List[Section]) -> Dict[str, List[Section]]:
        """Группировка секций по ключу (lower). Если ключи дублируются в разных файлах — все варианты сохраняем."""
        by_key: Dict[str, List[Section]] = {}
        for s in sections:
            by_key.setdefault(s.key, []).append(s)
        return by_key

    # --- UI сборка ---

    def build_ui(self) -> None:
        self.root.title("Context Docs")
        self.root.geometry("1150x750")
        self.root.minsize(950, 620)

        # Верхняя панель: Поиск + История + Кнопки
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=8, pady=6)

        tk.Label(top, text="Поиск по ключу:").pack(side="left")

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=6)

        self.btn_back = tk.Button(top, text="◀", width=3, command=self.go_back)
        self.btn_back.pack(side="left")
        self.btn_fwd = tk.Button(top, text="▶", width=3, command=self.go_forward)
        self.btn_fwd.pack(side="left", padx=(2, 8))

        tk.Button(top, text="Искать", command=self.do_search).pack(side="left", padx=6)
        tk.Button(top, text="Найти в дереве", command=self.focus_in_trees).pack(side="left")

        # Центральная область: слева — деревья, справа — контент
        main = tk.PanedWindow(self.root, sashrelief="raised", sashwidth=5)
        main.pack(fill="both", expand=True)

        # Слева: вкладки
        left = tk.Frame(main)
        main.add(left, minsize=320)

        nb = ttk.Notebook(left)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tree_cats = ttk.Treeview(nb, show="tree")
        self.tree_files = ttk.Treeview(nb, show="tree")
        nb.add(self.tree_cats, text="Категории")
        nb.add(self.tree_files, text="Файлы")

        # Заполняем деревья
        self._fill_categories_tree()
        self._fill_files_tree()

        # Привязываем двойной клик/Enter к открытию секции
        self.tree_cats.bind("<Double-1>", lambda e: self._on_tree_activate(self.tree_cats))
        self.tree_cats.bind("<Return>", lambda e: self._on_tree_activate(self.tree_cats))
        self.tree_files.bind("<Double-1>", lambda e: self._on_tree_activate(self.tree_files))
        self.tree_files.bind("<Return>", lambda e: self._on_tree_activate(self.tree_files))

        # Справа: верх — markdown, низ — код
        right = tk.Frame(main)
        main.add(right)

        # Верхний блок — полный markdown секции
        self.markdown_view = ScrolledText(right, wrap="word", height=18)
        self.markdown_view.pack(fill="both", expand=True, padx=6, pady=(6, 3))
        self.markdown_view.configure(state="disabled")

        # Нижний блок — выбор и показ кода
        code_panel = tk.Frame(right)
        code_panel.pack(fill="both", expand=False, padx=6, pady=(0, 6))

        header = tk.Frame(code_panel)
        header.pack(fill="x")
        tk.Label(header, text="Код‑блок:").pack(side="left")

        self.code_combo = ttk.Combobox(header, state="readonly", values=[])
        self.code_combo.pack(side="left", padx=6)
        self.code_combo.bind("<<ComboboxSelected>>", lambda e: self._update_code_view())

        self.code_view = ScrolledText(code_panel, wrap="none", height=12)
        self.code_view.configure(state="disabled")
        self.code_view.pack(fill="both", expand=True, pady=(3, 0))

        # Нижняя панель с кнопками действий
        btn_bar = tk.Frame(right)
        btn_bar.pack(fill="x", padx=6, pady=6)
        tk.Button(btn_bar, text="Скопировать весь блок", command=self.copy_markdown).pack(side="left", padx=4)
        tk.Button(btn_bar, text="Скопировать код", command=self.copy_code).pack(side="left", padx=4)
        tk.Button(btn_bar, text="Открыть .md", command=self.open_md).pack(side="left", padx=4)
        tk.Button(btn_bar, text="Закрыть", command=self.root.destroy).pack(side="right", padx=4)

        self._update_hist_buttons()

    # --- заполнение деревьев ---

    def _fill_categories_tree(self) -> None:
        """Строит дерево по строкам категорий (без фиктивного корня, без пустых уровней)."""
        self.tree_cats.delete(*self.tree_cats.get_children())

        def add_node(parent: str, subtree: Dict) -> None:
            # Сначала категории
            for name, node in sorted((k, v) for k, v in subtree.items() if k != "__sections__"):
                nid = self.tree_cats.insert(parent, "end", text=f"🏷️ {name}", open=False)
                add_node(nid, node)
            # Затем секции
            for sec in subtree.get("__sections__", []):
                self.tree_cats.insert(parent, "end", iid=make_section_iid(sec), text=f"§ {sec.key}")

        add_node("", self.cats_index)

    def _fill_files_tree(self) -> None:
        """Строит дерево по файловой структуре docs/…/file.md → § секции."""
        self.tree_files.delete(*self.tree_files.get_children())

        def add_node(parent: str, subtree: Dict) -> None:
            for name, node in sorted(subtree.items()):
                if isinstance(node, list):
                    # name — файл
                    fid = self.tree_files.insert(parent, "end", text=f"📄 {name}", open=False)
                    for sec in node:
                        self.tree_files.insert(fid, "end", iid=make_section_iid(sec), text=f"§ {sec.key}")
                else:
                    # name — директория
                    nid = self.tree_files.insert(parent, "end", text=f"📁 {name}", open=False)
                    add_node(nid, node)

        root_id = self.tree_files.insert("", "end", text=f"📚 {DOCS_ROOT.name}", open=True)
        add_node(root_id, build_files_index(self.sections))

    # --- действия пользователя ---

    def do_search(self) -> None:
        """Ищет секцию по ключу из строки поиска (точно или ближайшее совпадение)."""
        term = self.search_var.get().strip().lower()
        if not term:
            return

        hit_list = self.flat_by_key.get(term, [])
        if not hit_list:
            # попробуем ближайшее совпадение по ключам
            keys = list(self.flat_by_key.keys())
            close = difflib.get_close_matches(term, keys, n=1)
            if close:
                hit_list = self.flat_by_key.get(close[0], [])

        if not hit_list:
            messagebox.showinfo("Поиск", f"Нет описания для: {term}")
            return

        # Если ключ в нескольких файлах — берем первый
        self._open_section(hit_list[0], add_to_history=True)

    def _on_tree_activate(self, tree: ttk.Treeview) -> None:
        """Открывает секцию по двойному клику/Enter в дереве."""
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        if not iid.startswith("sec::"):
            return
        # Ищем секцию с таким iid (перебирать быстро — секций обычно не десятки тысяч)
        for s in self.sections:
            if make_section_iid(s) == iid:
                self._open_section(s, add_to_history=True)
                break

    def focus_in_trees(self) -> None:
        """Позиционирует оба дерева на текущей секции (раскрывая всю цепочку родителей)."""
        if not self.current:
            return
        target = make_section_iid(self.current)
        tree_find_and_focus(self.tree_files, target)
        tree_find_and_focus(self.tree_cats, target)

    def open_md(self) -> None:
        """Открыть исходный .md в системном браузере (file://)."""
        if not self.current:
            return
        webbrowser.open(self.current.file_path.as_uri())

    def copy_markdown(self) -> None:
        """Скопировать весь markdown секции."""
        if not self.current:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.current.markdown)

    def copy_code(self) -> None:
        """Скопировать выбранный код-блок из Combobox (если есть)."""
        if not self.current or not self.current.codes:
            return
        idx = self.code_combo.current()
        if 0 <= idx < len(self.current.codes):
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current.codes[idx])

    # --- отображение секции и история ---

    def _open_section(self, sec: Section, add_to_history: bool) -> None:
        """Показать секцию справа. При необходимости добавить в историю."""
        self.current = sec

        # Верхний markdown
        self.markdown_view.configure(state="normal")
        self.markdown_view.delete("1.0", "end")
        self.markdown_view.insert("1.0", sec.markdown)
        self.markdown_view.configure(state="disabled")

        # Нижняя панель кода
        if sec.codes:
            self.code_combo["values"] = [f"Блок {i + 1}" for i in range(len(sec.codes))]
            self.code_combo.current(0)
        else:
            self.code_combo["values"] = ["— нет кода —"]
            self.code_combo.current(0)
        self._update_code_view()

        # История
        if add_to_history:
            # обрезаем «хвост», если мы шли назад и затем открыли новую секцию
            if self.hist_idx < len(self.history) - 1:
                self.history = self.history[: self.hist_idx + 1]
            self.history.append(sec)
            self.hist_idx = len(self.history) - 1

        self._update_hist_buttons()

    def _update_code_view(self) -> None:
        """Обновить текст в нижнем поле кода в соответствии с выбранным блоком."""
        self.code_view.configure(state="normal")
        self.code_view.delete("1.0", "end")
        if self.current and self.current.codes:
            idx = self.code_combo.current()
            if 0 <= idx < len(self.current.codes):
                self.code_view.insert("1.0", self.current.codes[idx])
        self.code_view.configure(state="disabled")

    def go_back(self) -> None:
        """Назад по истории."""
        if self.hist_idx > 0:
            self.hist_idx -= 1
            self._open_section(self.history[self.hist_idx], add_to_history=False)

    def go_forward(self) -> None:
        """Вперед по истории."""
        if self.hist_idx < len(self.history) - 1:
            self.hist_idx += 1
            self._open_section(self.history[self.hist_idx], add_to_history=False)

    def _update_hist_buttons(self) -> None:
        """Активность кнопок истории в зависимости от позиции указателя."""
        state_back = "normal" if self.hist_idx > 0 else "disabled"
        state_fwd = "normal" if (0 <= self.hist_idx < len(self.history) - 1) else "disabled"
        self.btn_back.configure(state=state_back)
        self.btn_fwd.configure(state=state_fwd)


# -----------------------------------------------------------------------------
# ТОЧКА ВХОДА
# -----------------------------------------------------------------------------

def main(argv: List[str]) -> int:
    """
    Точка входа:
      - читает initial_term из argv[1] (если есть),
      - загружает секции,
      - запускает Tk-интерфейс.
    """
    initial_term = argv[1].strip() if len(argv) > 1 else ""

    if not DOCS_ROOT.exists():
        messagebox.showerror("Ошибка", f"Папка с документацией не найдена:\n{DOCS_ROOT}")
        return 2

    sections = load_all_sections(DOCS_ROOT)
    if not sections:
        messagebox.showwarning("Пусто", f"В {DOCS_ROOT} не найдено ни одной секции (*.md).")
        # продолжаем — чтобы хотя бы открыть пустое окно и поправить путь

    root = tk.Tk()
    app = App(root, sections, initial_term)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
