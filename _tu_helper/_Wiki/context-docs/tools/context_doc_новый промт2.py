#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_doc.py — локальная система контекстной документации для PyCharm (External Tool).
Требования см. README.md. Работает на Python 3.8+ и только на стандартной библиотеке.
"""
import sys
import os
import re
import difflib
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# ------------------------------- Константы -------------------------------

IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}
DOCS_ROOT = Path(__file__).parent.parent / "docs"

SEPARATOR_RE = re.compile(r'^\s*(?:[-]{3,}|[=]{3,})\s*$')
CODE_FENCE_START_RE = re.compile(r'^```.*$')
CODE_FENCE_END_RE = re.compile(r'^```$')

# ------------------------------- Модель -------------------------------

class Section:
    __slots__ = ("key", "categories", "markdown", "codes", "file_path", "anchor")
    def __init__(self, key, categories, markdown, codes, file_path, anchor):
        self.key = key                          # исходный ключ (регистрозависимый из ## ...)
        self.categories = categories[:]         # список категорий ['A', 'B', ...] (может быть пуст)
        self.markdown = markdown                # полный markdown секции для верхнего окна (включая строку ## ключ, без строки категорий)
        self.codes = codes[:]                   # список строк — содержимое каждого код-блока БЕЗ ограждений
        self.file_path = Path(file_path)        # путь к .md
        self.anchor = anchor                    # уникальный якорь внутри файла (порядковый номер секции)

# ------------------------------- Парсинг Markdown -------------------------------

def parse_markdown_file(fp: Path):
    """Парсит один .md файл на список Section по правилам из задания."""
    try:
        text = fp.read_text("utf-8")
    except Exception as e:
        print(f"Не удалось прочитать {fp}: {e}", file=sys.stderr)
        return []

    lines = text.splitlines()
    sections = []
    i = 0
    section_index = 0

    def is_separator(line: str) -> bool:
        return bool(SEPARATOR_RE.match(line))

    # Перемещаемся по строкам, ищем заголовки ##
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("## "):
            # Новый раздел
            key = line.lstrip()[3:].strip()
            i += 1

            # Пропускаем любые пустые и разделительные перед строкой категорий
            while i < len(lines) and (not lines[i].strip() or is_separator(lines[i])):
                i += 1

            # Следующая непустая и неразделительная — это строка категорий
            categories = []
            if i < len(lines) and lines[i].strip() and not is_separator(lines[i]):
                cat_line = lines[i].strip()
                # Категории разделены " - "
                categories = [c.strip() for c in cat_line.split(" - ") if c.strip()]
                i += 1
            # После строки категорий могут идти разделители — игнорируем их
            while i < len(lines) and (not lines[i].strip() or is_separator(lines[i])):
                # ВАЖНО: если это пустые/разделители, то они не включаются в верхний markdown
                i += 1

            # Собираем тело секции до следующего "## " (или конца файла)
            body_lines = []
            while i < len(lines) and not lines[i].lstrip().startswith("## "):
                body_lines.append(lines[i])
                i += 1

            # Извлекаем коды (тройные бэктики), сохраняя в markdown сами ограждения
            codes = []
            in_code = False
            current_code = []
            for bl in body_lines:
                if not in_code and CODE_FENCE_START_RE.match(bl):
                    in_code = True
                    current_code = []
                    continue
                if in_code and CODE_FENCE_END_RE.match(bl):
                    in_code = False
                    codes.append("\n".join(current_code))
                    current_code = []
                    continue
                if in_code:
                    current_code.append(bl)

            # Формируем markdown для верхнего окна: включаем строку ## ключ и далее body_lines
            section_md = "## " + key + "\n" + "\n".join(body_lines).rstrip()

            section_index += 1
            sections.append(Section(
                key=key,
                categories=categories,
                markdown=section_md,
                codes=codes,
                file_path=fp,
                anchor=f"sec-{section_index}"
            ))
        else:
            i += 1

    return sections

def load_all_sections(root: Path):
    """Рекурсивно обходит docs/, возвращает (sections, by_key_first, per_file_sections)."""
    sections = []
    per_file_sections = {}   # Path -> [Section, ...]
    by_key_first = {}        # lower(key) -> Section (первое вхождение)

    for dirpath, dirnames, filenames in os.walk(root):
        # Фильтрация игнорируемых директорий
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for fn in filenames:
            if fn.lower().endswith(".md"):
                fp = Path(dirpath) / fn
                secs = parse_markdown_file(fp)
                if secs:
                    per_file_sections.setdefault(fp, []).extend(secs)
                    for s in secs:
                        sections.append(s)
                        lk = s.key.lower()
                        if lk not in by_key_first:
                            by_key_first[lk] = s
    return sections, by_key_first, per_file_sections

# ------------------------------- UI -------------------------------

class App(tk.Tk):
    def __init__(self, initial_term: str):
        super().__init__()
        self.title("Context Docs")
        self.geometry("1100x700")

        # Данные
        self.sections, self.by_key_first, self.per_file_sections = load_all_sections(DOCS_ROOT)
        self.current_section = None
        self.history = []    # список Section
        self.hist_index = -1 # индекс текущего
        self.initial_term = (initial_term or "").strip()

        # Маппинги для позиционирования в деревьях
        self.cat_tree_item_by_section = {}   # Section -> item_id
        self.file_tree_item_by_section = {}  # Section -> item_id

        # Верхняя панель поиска
        self._build_search_bar()

        # Основной сплит: слева вкладки деревьев, справа два вертикальных блока
        self._build_main_panes()

        # Заполнение деревьев
        self._populate_category_tree()
        self._populate_file_tree()

        # Первичный поиск если initial_term задан
        if self.initial_term:
            self.search_var.set(self.initial_term)
            self.do_search()
        else:
            # При пустом — просто открыть окно без выбора
            pass

        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----------- Построение UI -----------
    def _build_search_bar(self):
        bar = ttk.Frame(self)
        bar.pack(side="top", fill="x")

        ttk.Label(bar, text="Поиск по ключу:").pack(side="left", padx=(8,4), pady=8)

        self.search_var = tk.StringVar(value="")
        self.search_entry = ttk.Entry(bar, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=4)
        self.search_entry.bind("<Return>", lambda e: self.do_search())

        self.btn_back = ttk.Button(bar, text="◀", width=3, command=self.go_back)
        self.btn_back.pack(side="left", padx=2)
        self.btn_forward = ttk.Button(bar, text="▶", width=3, command=self.go_forward)
        self.btn_forward.pack(side="left", padx=2)

        ttk.Button(bar, text="Искать", command=self.do_search).pack(side="left", padx=6)
        ttk.Button(bar, text="Найти в дереве", command=self.focus_current_in_trees).pack(side="left", padx=2)

    def _build_main_panes(self):
        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True)

        # Левая панель — вкладки
        left = ttk.Notebook(main)
        self.tab_categories = ttk.Frame(left)
        self.tab_files = ttk.Frame(left)
        left.add(self.tab_categories, text="Категории")
        left.add(self.tab_files, text="Файлы")

        # Дерево категорий
        self.tree_cat = ttk.Treeview(self.tab_categories, show="tree")
        self.tree_cat.pack(fill="both", expand=True)
        self.tree_cat.bind("<Double-1>", self._on_tree_cat_activate)
        self.tree_cat.bind("<Return>", self._on_tree_cat_activate)

        # Дерево файлов
        self.tree_files = ttk.Treeview(self.tab_files, show="tree")
        self.tree_files.pack(fill="both", expand=True)
        self.tree_files.bind("<Double-1>", self._on_tree_files_activate)
        self.tree_files.bind("<Return>", self._on_tree_files_activate)

        main.add(left, weight=1)

        # Правая панель — вертикальный сплит из двух блоков
        right = ttk.Panedwindow(main, orient="vertical")
        main.add(right, weight=3)

        # Верхний блок — полный markdown секции
        top_frame = ttk.Frame(right)
        self.markdown_text = ScrolledText(top_frame, wrap="word", state="disabled")
        self.markdown_text.pack(fill="both", expand=True)
        right.add(top_frame, weight=3)

        # Нижний блок — панель кода
        bottom_frame = ttk.Frame(right)
        # Комбо
        self.code_var = tk.StringVar()
        self.code_combo = ttk.Combobox(bottom_frame, textvariable=self.code_var, state="readonly", values=["— нет кода —"])
        self.code_combo.current(0)
        self.code_combo.pack(fill="x", padx=6, pady=6)
        self.code_combo.bind("<<ComboboxSelected>>", lambda e: self._render_code_block())

        # Текст кода
        self.code_text = ScrolledText(bottom_frame, wrap="none", state="disabled", height=12)
        self.code_text.pack(fill="both", expand=True, padx=6, pady=(0,6))

        # Нижние кнопки справа
        btns = ttk.Frame(bottom_frame)
        btns.pack(fill="x", padx=6, pady=(0,8))
        ttk.Button(btns, text="Скопировать весь блок", command=self.copy_full_markdown).pack(side="left", padx=2)
        ttk.Button(btns, text="Скопировать код", command=self.copy_code_block).pack(side="left", padx=2)
        ttk.Button(btns, text="Открыть .md", command=self.open_markdown_file).pack(side="left", padx=2)
        ttk.Button(btns, text="Закрыть", command=self.on_close).pack(side="right", padx=2)

        right.add(bottom_frame, weight=2)

    # ----------- Заполнение деревьев -----------
    def _populate_category_tree(self):
        # Создаем иерархию категорий: dict[path_tuple] -> item_id
        self.cat_nodes = {}
        # Убираем фиктивный корень
        for s in self.sections:
            # Строим цепочку категорий
            parent_id = ""
            path = []
            for cat in s.categories:
                path.append(cat)
                tup = tuple(path)
                if tup not in self.cat_nodes:
                    item_id = self.tree_cat.insert(parent_id, "end", text=cat, open=False)
                    self.cat_nodes[tup] = item_id
                    parent_id = item_id
                else:
                    parent_id = self.cat_nodes[tup]
            # Добавляем лист — саму секцию
            sec_text = f"§ {s.key}"
            sec_id = self.tree_cat.insert(parent_id, "end", text=sec_text, open=False, values=("section",))
            self.cat_tree_item_by_section[s] = sec_id

    def _populate_file_tree(self):
        # Структура файлов
        # Создаем узлы для директорий и файлов. Под файлом — § секции.
        self.file_nodes = {}  # path -> item_id
        # Корневой
        root_id = self.tree_files.insert("", "end", text=str(DOCS_ROOT.name), open=True)
        self.file_nodes[DOCS_ROOT] = root_id

        # Обходим дерево каталогов с сохранением порядка
        for dirpath, dirnames, filenames in os.walk(DOCS_ROOT):
            # Фильтрация игнорируемых директорий
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            dirpath = Path(dirpath)

            # Узел текущей папки
            parent_id = self.file_nodes.get(dirpath, None)
            if parent_id is None:
                # Создать родительские узлы если нужно
                parts = dirpath.relative_to(DOCS_ROOT).parts
                cur = DOCS_ROOT
                parent = root_id
                for p in parts:
                    cur = cur / p
                    if cur not in self.file_nodes:
                        nid = self.tree_files.insert(parent, "end", text=p, open=False)
                        self.file_nodes[cur] = nid
                        parent = nid
                    else:
                        parent = self.file_nodes[cur]
                parent_id = parent

            # Сначала директории
            for d in sorted(dirnames):
                p = dirpath / d
                if p not in self.file_nodes:
                    nid = self.tree_files.insert(parent_id, "end", text=d, open=False)
                    self.file_nodes[p] = nid

            # Затем файлы
            for fn in sorted(filenames):
                if not fn.lower().endswith(".md"):
                    continue
                fp = dirpath / fn
                fid = self.tree_files.insert(parent_id, "end", text=fn, open=False)
                self.file_nodes[fp] = fid

                # Под файлом — секции
                for s in self.per_file_sections.get(fp, []):
                    sec_text = f"§ {s.key}"
                    sid = self.tree_files.insert(fid, "end", text=sec_text, open=False, values=("section",))
                    self.file_tree_item_by_section[s] = sid

    # ----------- Действия -----------
    def do_search(self):
        term = (self.search_var.get() or "").strip()
        if not term:
            messagebox.showinfo("Поиск", "Введите ключ секции (заголовок после '## ').")
            return

        # Точный поиск (по первому совпадению)
        s = self.by_key_first.get(term.lower())
        if s is None:
            # Fuzzy по ключам
            choices = list(self.by_key_first.keys())
            close = difflib.get_close_matches(term.lower(), choices, n=1, cutoff=0.5)
            if close:
                s = self.by_key_first[close[0]]

        if s is None:
            messagebox.showwarning("Не найдено", f"Секция по ключу '{term}' не найдена.")
            return

        self.open_section(s, add_to_history=True)

    def open_section(self, section: Section, add_to_history: bool = True):
        if section is None:
            return
        self.current_section = section

        # Верхний блок — markdown
        self.markdown_text.configure(state="normal")
        self.markdown_text.delete("1.0", "end")
        self.markdown_text.insert("1.0", section.markdown if section.markdown.strip() else f"## {section.key}\n")
        self.markdown_text.configure(state="disabled")

        # Нижняя панель — коды
        if section.codes:
            values = [f"Блок {i+1}" for i in range(len(section.codes))]
        else:
            values = ["— нет кода —"]
        self.code_combo.configure(values=values)
        self.code_combo.current(0)
        self._render_code_block()

        # История
        if add_to_history:
            # обрезаем "вперед" если было
            if self.hist_index < len(self.history) - 1:
                self.history = self.history[:self.hist_index+1]
            self.history.append(section)
            self.hist_index = len(self.history) - 1
        self._update_nav_buttons_state()

    def _render_code_block(self):
        self.code_text.configure(state="normal")
        self.code_text.delete("1.0", "end")
        if self.current_section and self.current_section.codes:
            idx = self.code_combo.current()
            if 0 <= idx < len(self.current_section.codes):
                self.code_text.insert("1.0", self.current_section.codes[idx])
        self.code_text.configure(state="disabled")

    def _update_nav_buttons_state(self):
        self.btn_back.configure(state="normal" if self.hist_index > 0 else "disabled")
        self.btn_forward.configure(state="normal" if self.hist_index < len(self.history) - 1 else "disabled")

    def go_back(self):
        if self.hist_index > 0:
            self.hist_index -= 1
            self.open_section(self.history[self.hist_index], add_to_history=False)
            self._update_nav_buttons_state()

    def go_forward(self):
        if self.hist_index < len(self.history) - 1:
            self.hist_index += 1
            self.open_section(self.history[self.hist_index], add_to_history=False)
            self._update_nav_buttons_state()

    # ----------- Деревья: активация -----------
    def _on_tree_cat_activate(self, event):
        item_id = self.tree_cat.focus()
        if not item_id:
            return
        text = self.tree_cat.item(item_id, "text")
        if text.startswith("§ "):
            # Найти соответствующую секцию
            for s, iid in self.cat_tree_item_by_section.items():
                if iid == item_id:
                    self.open_section(s, add_to_history=True)
                    break

    def _on_tree_files_activate(self, event):
        item_id = self.tree_files.focus()
        if not item_id:
            return
        text = self.tree_files.item(item_id, "text")
        if text.startswith("§ "):
            for s, iid in self.file_tree_item_by_section.items():
                if iid == item_id:
                    self.open_section(s, add_to_history=True)
                    break

    # ----------- Позиционирование текущей секции в деревьях -----------
    def focus_current_in_trees(self):
        s = self.current_section
        if s is None:
            return
        # Категории
        iid = self.cat_tree_item_by_section.get(s)
        if iid:
            self._focus_and_see(self.tree_cat, iid)

        # Файлы
        iid2 = self.file_tree_item_by_section.get(s)
        if iid2:
            self._focus_and_see(self.tree_files, iid2)

    def _focus_and_see(self, tree: ttk.Treeview, item_id: str):
        # Развернуть всех родителей
        pid = tree.parent(item_id)
        while pid:
            tree.item(pid, open=True)
            pid = tree.parent(pid)
        tree.see(item_id)
        tree.selection_set(item_id)
        tree.focus(item_id)

    # ----------- Буфер/Открытие -----------
    def copy_full_markdown(self):
        if not self.current_section:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current_section.markdown)

    def copy_code_block(self):
        if not self.current_section:
            return
        text = ""
        if self.current_section.codes:
            idx = self.code_combo.current()
            if 0 <= idx < len(self.current_section.codes):
                text = self.current_section.codes[idx]
        self.clipboard_clear()
        self.clipboard_append(text)

    def open_markdown_file(self):
        if not self.current_section:
            return
        try:
            webbrowser.open(self.current_section.file_path.as_uri())
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def on_close(self):
        self.destroy()

# ------------------------------- main -------------------------------

def main():
    # Аргумент 1 — initial_term (может быть пустым)
    initial_term = ""
    if len(sys.argv) >= 2:
        initial_term = sys.argv[1]
    app = App(initial_term=initial_term)
    app.mainloop()

if __name__ == "__main__":
    main()
