# ui_app.py
# -*- coding: utf-8 -*-
"""
Tkinter-интерфейс: одно дерево категорий, справа markdown+путь и кодовые блоки,
сверху поиск через Combobox + кнопки истории (◀ ▶).
"""

from __future__ import annotations
import webbrowser
from typing import Dict, Optional, List

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

from config_roots import read_doc_roots
from md_parser import collect_sections_from_roots
from search_index import SearchIndex
from ui_tree import add_section_to_tree
from models import Section
from utils import normalize_key

APP_TITLE = "Context Docs Viewer"

class App:
    def __init__(self, root: tk.Tk, initial_query: str = ""):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("1150x780")
        root.minsize(900, 600)

        # корни и секции
        self.doc_roots = read_doc_roots()
        self.all_files, self.sections = collect_sections_from_roots(self.doc_roots)

        if not self.all_files:
            messagebox.showwarning(
                "Файлы не найдены",
                "Не найдено .md файлов в корнях:\n\n" + "\n".join(str(p) for p in self.doc_roots)
            )
        elif not self.sections:
            messagebox.showwarning(
                "Секции не найдены",
                f"Найдено .md файлов: {len(self.all_files)}, но секции не распознаны.\n"
                "Проверьте, что заголовки начинаются с '#' или '##'."
            )

        # индекс
        self.index = SearchIndex(self.sections)

        # состояние: текущая секция и ИСТОРИЯ поиска/открытий
        self.current_section: Optional[Section] = None
        self.history: List[str] = []     # храним КЛЮЧИ
        self.hist_idx: int = -1          # -1 = пусто

        self._build_topbar()
        self._build_body()
        self._fill_categories_tree()

        if initial_query:
            self.search_combo.set(initial_query)
            self.open_best_from_combo()  # это добавит запись в историю

    # ---------------- верхняя панель (поиск + история) ----------------
    def _build_topbar(self) -> None:
        top = ttk.Frame(self.root, padding=6)
        top.pack(side=tk.TOP, fill=tk.X)

        # кнопки истории
        self.btn_back = ttk.Button(top, text="◀", width=3, command=self.nav_back)
        self.btn_back.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_fwd  = ttk.Button(top, text="▶", width=3, command=self.nav_forward)
        self.btn_fwd.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(top, text="Поиск по ключу:").pack(side=tk.LEFT, padx=(0, 6))

        # Combobox в режиме ввода текста
        self.search_combo = ttk.Combobox(top, state="normal", values=[], width=42)
        self.search_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # обновление подсказок при наборе
        self.search_combo.bind("<KeyRelease>", self._on_query_changed)
        # Enter — открыть лучшую
        self.search_combo.bind("<Return>", lambda e: self.open_best_from_combo())

        ttk.Button(top, text="Открыть", command=self.open_best_from_combo).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Найти в дереве", command=self.locate_in_tree).pack(side=tk.LEFT)

        self._update_hist_buttons()

    # ---------------- тело окна ----------------
    def _build_body(self) -> None:
        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        # слева — дерево категорий
        left = ttk.Frame(body)
        body.add(left, weight=1)

        self.cat_tree = ttk.Treeview(left, show="tree")
        self.cat_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.cat_tree.bind("<Double-1>", self._on_tree_activate)
        self.cat_tree.bind("<Return>", self._on_tree_activate)

        # справа — верх: markdown + путь; низ — код
        right = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        body.add(right, weight=3)

        # верх
        md_wrap = ttk.Frame(right, padding=6)
        right.add(md_wrap, weight=3)

        self.md_text = ScrolledText(md_wrap, wrap="word")
        self.md_text.pack(fill=tk.BOTH, expand=True)
        self.md_text.configure(state="disabled")

        path_bar = ttk.Frame(md_wrap)
        path_bar.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(path_bar, text="Файл:").pack(side=tk.LEFT)
        self.path_value = ttk.Entry(path_bar, state="readonly")
        self.path_value.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        # низ
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

    # ---------------- заполнение дерева ----------------
    def _fill_categories_tree(self) -> None:
        self.cat_tree.delete(*self.cat_tree.get_children())

        # счётчик вхождений одной и той же секции (для уникальных iid)
        per_file_counter: Dict[str, int] = {}

        for s in self.sections:
            paths = s.categories_list or [["Без категории"]]
            for cat_path in paths:
                k = str(s.file_path.resolve())
                per_file_counter[k] = per_file_counter.get(k, 0) + 1
                add_section_to_tree(self.cat_tree, "", cat_path, s, per_file_counter[k])

    # ---------------- поиск ----------------
    def _on_query_changed(self, event=None) -> None:
        q = self.search_combo.get().strip()
        keys = self.index.suggest(q, limit=50)

        exact = normalize_key(q)
        if exact in keys:
            ordered = [exact] + [k for k in keys if k != exact]
        else:
            ordered = keys

        out = []
        for k in ordered:
            sec = self.index.by_key.get(k)
            if not sec:
                continue
            out.append(f"{k}    —    {sec.file_path.name}")

        self.search_combo["values"] = out

    def _extract_key_from_combo(self) -> str:
        raw = self.search_combo.get().strip()
        parts = raw.split("—")
        if len(parts) >= 2:
            return parts[0].strip()
        return raw

    def open_best_from_combo(self) -> None:
        """Открыть лучшую секцию под введённый текст + добавить в историю."""
        q = self._extract_key_from_combo()
        if not q:
            messagebox.showinfo("Поиск", "Введите ключ для поиска.")
            return
        sec = self.index.find_best(q)
        if not sec:
            messagebox.showinfo("Поиск", f"Ничего не найдено для: {q}")
            return
        self.open_section(sec, add_to_history=True)

    # ---------------- открытие секции ----------------
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
            self.open_section(sec, add_to_history=True)

    def open_section(self, sec: Section, add_to_history: bool) -> None:
        """Показать секцию и при необходимости добавить запись в историю."""
        self.current_section = sec

        header = f"# {sec.display_key}"
        self.md_text.configure(state="normal")
        self.md_text.delete("1.0", "end")
        self.md_text.insert("1.0", header + "\n\n")
        if sec.markdown:
            self.md_text.insert("end", sec.markdown)
        self.md_text.configure(state="disabled")

        # путь к файлу
        try:
            self.path_value.configure(state="normal")
            self.path_value.delete(0, "end")
            self.path_value.insert(0, str(sec.file_path.resolve()))
        finally:
            self.path_value.configure(state="readonly")

        # код-блоки
        if sec.codes:
            items = [f"Блок #{i+1} — {len(c.splitlines())} строк" for i, c in enumerate(sec.codes)]
            self.code_combo["values"] = items
            self.code_combo.current(0)
        else:
            self.code_combo["values"] = ["— нет кода —"]
            self.code_combo.current(0)
        self._update_code_view()

        # история
        if add_to_history:
            # если мы были «внутри истории» (не на последнем элементе) — обрежем хвост
            if self.hist_idx < len(self.history) - 1:
                self.history = self.history[: self.hist_idx + 1]
            # кладём ключ; если предыдущий совпадает — не дублируем
            if not self.history or self.history[-1] != sec.key:
                self.history.append(sec.key)
            self.hist_idx = len(self.history) - 1
            self._update_hist_buttons()

    # ---------------- кодовые блоки / буфер ----------------
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

    # ---------------- позиционирование и история ----------------
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

    def nav_back(self) -> None:
        """Шаг назад по истории (если есть)."""
        if self.hist_idx > 0:
            self.hist_idx -= 1
            key = self.history[self.hist_idx]
            sec = self.index.by_key.get(key)
            if sec:
                # при навигации по истории НЕ добавляем запись в историю
                self.open_section(sec, add_to_history=False)
            self._update_hist_buttons()

    def nav_forward(self) -> None:
        """Шаг вперёд по истории (если есть)."""
        if 0 <= self.hist_idx < len(self.history) - 1:
            self.hist_idx += 1
            key = self.history[self.hist_idx]
            sec = self.index.by_key.get(key)
            if sec:
                self.open_section(sec, add_to_history=False)
            self._update_hist_buttons()

    def _update_hist_buttons(self) -> None:
        """Активировать/деактивировать кнопки ◀ ▶ в зависимости от позиции."""
        self.btn_back.configure(state=("normal" if self.hist_idx > 0 else "disabled"))
        enable_fwd = (0 <= self.hist_idx < len(self.history) - 1)
        self.btn_fwd.configure(state=("normal" if enable_fwd else "disabled"))
