#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Docs Viewer — локальный просмотрщик документации из Markdown с расширенным поиском.
Один файл. Только стандартная библиотека. Python 3.8+.

СТРУКТУРА КОДА (соблюдена как в задании):
1) Докстринг (вы здесь)
2) Импорты
3) Константы
4) Парсинг Markdown (.md)
5) Поиск (точный, подстрочный, "fuzzy" + токенизация)
6) Построение деревьев (категории, файлы)
7) Утилиты (нормализация, открытие файла, буфер обмена)
8) Класс App_UI (UI по точной схеме)
9) main()
10) if __name__ == '__main__': main()

Как пользоваться:
- Запуск без аргумента: python context_doc.py
- Запуск с автопоиском: python context_doc.py "ul-ol-li"
- По умолчанию сканируем папку docs/, которая должна быть НА УРОВЕНЬ ВЫШЕ скрипта.
  Т.е. структура: <project>/tools/context_doc.py и <project>/docs/*.md
"""

# =======================
# 2) ИМПОРТЫ
# =======================
import os
import re
import sys
import json
import math
import difflib
import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# =======================
# 3) КОНСТАНТЫ
# =======================

DEFAULT_DOCS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "docs"))
IGNORE_DIRS = {"node_modules", ".git", "site", ".venv", "venv", "__pycache__"}

RE_HEADER = re.compile(r'^##\s+(.+?)\s*$', re.IGNORECASE)
RE_SEPARATOR = re.compile(r'^\s*(?:={3,}|-{3,})\s*$')
RE_CATEGORIES = re.compile(r'^\s*categories\s*:\s*(.+)$', re.IGNORECASE)
RE_ALIASES = re.compile(r'^\s*aliases\s*:\s*(.+)$', re.IGNORECASE)
RE_CODE_FENCE = re.compile(r'^```([\w#+.-]*)\s*$')

# =======================
# 4) СТРУКТУРЫ ДАННЫХ
# =======================

@dataclass
class CodeBlock:
    lang: str
    code: str

@dataclass
class Section:
    display_key: str
    key: str
    tokens: List[str]
    categories: List[str]
    aliases: List[str]
    file_path: str
    rel_path: str
    start_line: int
    markdown: str
    code_blocks: List[CodeBlock] = field(default_factory=list)

Sections = List[Section]

# =======================
# 4) ПАРСИНГ
# =======================

def normalize_text(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s

def tokenize_key(s: str) -> List[str]:
    s = normalize_text(s)
    tokens = re.split(r'[^a-z0-9_]+', s)
    return [t for t in tokens if t]

def try_read_text(path: str) -> Optional[str]:
    for enc in ('utf-8', 'cp1251'):
        try:
            with open(path, 'r', encoding=enc, errors='strict') as f:
                return f.read()
        except Exception:
            continue
    return None

def iterate_md_files(root: str) -> List[str]:
    md_paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if name.lower().endswith('.md'):
                md_paths.append(os.path.join(dirpath, name))
    return md_paths

def parse_markdown_sections(file_path: str, docs_root: str) -> Sections:
    text = try_read_text(file_path)
    if text is None:
        return []
    lines = text.splitlines()
    sections: Sections = []

    i = 0
    while i < len(lines):
        m = RE_HEADER.match(lines[i])
        if not m:
            i += 1
            continue

        display_key = m.group(1).strip()
        key_norm = normalize_text(display_key)
        tokens = tokenize_key(display_key)

        categories: List[str] = []
        aliases: List[str] = []

        i += 1
        while i < len(lines) and RE_SEPARATOR.match(lines[i]):
            i += 1

        while i < len(lines):
            if RE_HEADER.match(lines[i]):
                break
            if not lines[i].strip():
                i += 1
                continue
            mc = RE_CATEGORIES.match(lines[i])
            if mc:
                categories = [p.strip() for p in re.split(r'\s*-\s*', mc.group(1).strip()) if p.strip()]
                i += 1
                continue
            ma = RE_ALIASES.match(lines[i])
            if ma:
                parts = re.split(r'[;,]\s*|\s+', ma.group(1).strip())
                aliases = [normalize_text(p) for p in parts if p.strip()]
                i += 1
                continue
            break

        start_line = i
        content_lines = []
        while i < len(lines) and not RE_HEADER.match(lines[i]):
            content_lines.append(lines[i])
            i += 1
        markdown = "\n".join(content_lines).strip("\n")

        code_blocks: List[CodeBlock] = []
        in_code = False
        code_lang = ""
        buf = []

        for ln in content_lines:
            mc = RE_CODE_FENCE.match(ln)
            if mc:
                if not in_code:
                    in_code = True
                    code_lang = (mc.group(1) or "").strip()
                    buf = []
                else:
                    code_blocks.append(CodeBlock(lang=code_lang, code="\n".join(buf)))
                    in_code = False
                    code_lang = ""
                    buf = []
                continue
            if in_code:
                buf.append(ln)
        if in_code:
            code_blocks.append(CodeBlock(lang=code_lang, code="\n".join(buf)))

        rel_path = os.path.relpath(file_path, docs_root)

        sections.append(Section(
            display_key=display_key,
            key=key_norm,
            tokens=tokens,
            categories=categories,
            aliases=aliases,
            file_path=file_path,
            rel_path=rel_path,
            start_line=start_line + 1,
            markdown=markdown,
            code_blocks=code_blocks,
        ))
    return sections

def load_all_sections(docs_root: str) -> Sections:
    sections: Sections = []
    for path in iterate_md_files(docs_root):
        sections.extend(parse_markdown_sections(path, docs_root))
    return sections

# =======================
# 5) ПОИСК
# =======================

def unique_preserve_order(items: List[Section]) -> List[Section]:
    seen = set()
    out = []
    for it in items:
        if id(it) not in seen:
            seen.add(id(it))
            out.append(it)
    return out

def search_sections(sections: Sections, query: str) -> Tuple[Optional[Section], List[Section]]:
    q = normalize_text(query)
    if not q:
        return None, []
    q_tokens = tokenize_key(q)

    for s in sections:
        if s.key == q:
            candidates = [s] + [c for c in sections if c is not s and (q in c.key or q in " ".join(c.aliases))]
            return s, unique_preserve_order(candidates)

    for s in sections:
        if q in s.aliases:
            candidates = [s] + [c for c in sections if c is not s and (q in c.key or q in " ".join(c.aliases))]
            return s, unique_preserve_order(candidates)

    scored = []
    for s in sections:
        score = 0
        if q in s.key:
            score += 3
        if any(q in a for a in s.aliases):
            score += 2
        if q_tokens:
            inter = len(set(q_tokens).intersection(set(s.tokens)))
            if inter:
                score += 1 + inter
        if score > 0:
            scored.append((score, s))
    scored.sort(key=lambda t: (-t[0], t[1].display_key))

    label_to_section: Dict[str, Section] = {}
    for s in sections:
        label_to_section[s.display_key] = s
        for a in s.aliases:
            label_to_section[a] = s

    fuzzy_labels = difflib.get_close_matches(q, label_to_section.keys(), n=10, cutoff=0.6)
    fuzzy_candidates = [label_to_section[lbl] for lbl in fuzzy_labels]

    combined = unique_preserve_order([s for _, s in scored] + fuzzy_candidates)
    return None, combined

# =======================
# 6) ДЕРЕВЬЯ ДЛЯ UI
# =======================

def build_category_tree(sections: Sections) -> Dict:
    root: Dict = {}
    for s in sections:
        node = root
        for part in s.categories or ["Без категории"]:
            node = node.setdefault(part, {})
        node.setdefault("__sections__", []).append(s)
    return root

def build_files_tree(sections: Sections, docs_root: str) -> Dict:
    tree: Dict = {}
    for s in sections:
        rel = s.rel_path.replace("\\", "/")
        parts = rel.split("/")
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault(parts[-1], []).append(s)
    return tree

# =======================
# 7) УТИЛИТЫ
# =======================

def open_in_system(path: str) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{path}"')
        else:
            os.system(f'xdg-open "{path}"')
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")

def to_clipboard(root: tk.Tk, text: str) -> None:
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
    except Exception:
        pass

# =======================
# 8) UI
# =======================

class App_UI:
    def __init__(self, root: tk.Tk, sections: Sections, docs_root: str, initial_query: str = ""):
        self.root = root
        self.sections = sections
        self.docs_root = docs_root

        self.history: List[Section] = []
        self.history_pos: int = -1
        self.current: Optional[Section] = None

        # Хэш-ключ — id(section), чтобы не требовать hash у dataclass
        self.section_to_cat_nodes: Dict[int, str] = {}
        self.section_to_file_nodes: Dict[int, str] = {}

        self._build_ui()
        self._populate_trees()

        if initial_query:
            self.search_and_open(initial_query)

    def _build_ui(self) -> None:
        self.root.title("Context Docs Viewer")
        self.root.geometry("1100x700")

        topbar = ttk.Frame(self.root, padding=6)
        topbar.pack(side=tk.TOP, fill=tk.X)

        self.btn_back = ttk.Button(topbar, text="◀", width=3, command=self._go_back)
        self.btn_back.pack(side=tk.LEFT)
        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)

        self.btn_forward = ttk.Button(topbar, text="▶", width=3, command=self._go_forward)
        self.btn_forward.pack(side=tk.LEFT)
        ttk.Frame(topbar, width=10).pack(side=tk.LEFT)

        ttk.Label(topbar, text="Поиск:").pack(side=tk.LEFT)

        self.entry_query = ttk.Entry(topbar)
        self.entry_query.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry_query.bind("<Return>", lambda e: self._on_search())

        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)
        ttk.Button(topbar, text="Искать", command=self._on_search).pack(side=tk.LEFT)
        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)
        ttk.Button(topbar, text="Найти в дереве", command=self._find_in_trees).pack(side=tk.LEFT)

        paned_main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left_frame = ttk.Frame(paned_main)
        paned_main.add(left_frame, weight=1)

        nb = ttk.Notebook(left_frame)
        nb.pack(fill=tk.BOTH, expand=True)

        tab_cat = ttk.Frame(nb)
        nb.add(tab_cat, text="Категории")
        self.tree_cat = ttk.Treeview(tab_cat, show="tree")
        self.tree_cat.pack(fill=tk.BOTH, expand=True)
        self.tree_cat.bind("<Double-1>", self._on_cat_double_click)

        tab_files = ttk.Frame(nb)
        nb.add(tab_files, text="Файлы")
        self.tree_files = ttk.Treeview(tab_files, show="tree")
        self.tree_files.pack(fill=tk.BOTH, expand=True)
        self.tree_files.bind("<Double-1>", self._on_files_double_click)

        right_paned = ttk.PanedWindow(paned_main, orient=tk.VERTICAL)
        paned_main.add(right_paned, weight=3)

        top_right = ttk.Frame(right_paned, padding=6)
        right_paned.add(top_right, weight=3)

        self.txt_md = tk.Text(top_right, wrap=tk.NONE, font=("Consolas", 11))
        self.txt_md.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scr1 = ttk.Scrollbar(top_right, orient=tk.VERTICAL, command=self.txt_md.yview)
        scr1.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_md.configure(yscrollcommand=scr1.set)

        bottom_right = ttk.Frame(right_paned, padding=6)
        right_paned.add(bottom_right, weight=2)

        row_top = ttk.Frame(bottom_right)
        row_top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(row_top, text="Кодовые блоки:").pack(side=tk.LEFT)
        ttk.Frame(row_top, width=6).pack(side=tk.LEFT)

        self.combo_codes = ttk.Combobox(row_top, state="readonly")
        self.combo_codes.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.combo_codes.bind("<<ComboboxSelected>>", lambda e: self._show_selected_code())

        self.txt_code = tk.Text(bottom_right, wrap=tk.NONE, font=("Consolas", 11), height=12)
        self.txt_code.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scr2 = ttk.Scrollbar(bottom_right, orient=tk.VERTICAL, command=self.txt_code.yview)
        scr2.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_code.configure(yscrollcommand=scr2.set)

        row_bottom = ttk.Frame(bottom_right)
        row_bottom.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))

        ttk.Button(row_bottom, text="Скопировать весь блок", command=self._copy_markdown).pack(side=tk.LEFT)
        ttk.Frame(row_bottom, width=4).pack(side=tk.LEFT)
        ttk.Button(row_bottom, text="Скопировать код", command=self._copy_code).pack(side=tk.LEFT)
        ttk.Frame(row_bottom, width=4).pack(side=tk.LEFT)
        ttk.Button(row_bottom, text="Открыть .md", command=self._open_file).pack(side=tk.LEFT)
        ttk.Button(row_bottom, text="Закрыть", command=self.root.destroy).pack(side=tk.RIGHT)

    def _populate_trees(self) -> None:
        cat_tree = build_category_tree(self.sections)
        self.tree_cat.delete(*self.tree_cat.get_children())
        self.section_to_cat_nodes.clear()
        self._fill_cat_tree("", cat_tree)

        files_tree = build_files_tree(self.sections, self.docs_root)
        self.tree_files.delete(*self.tree_files.get_children())
        self.section_to_file_nodes.clear()
        self._fill_files_tree("", files_tree)

    def _fill_cat_tree(self, parent, node_dict: Dict) -> None:
        for name, sub in sorted(node_dict.items(), key=lambda kv: kv[0].lower()):
            if name == "__sections__":
                for s in sorted(sub, key=lambda x: x.display_key.lower()):
                    text = f"§ {s.display_key} ({s.rel_path})"
                    item_id = self.tree_cat.insert(parent, "end", text=text, values=(s.file_path,))
                    self.section_to_cat_nodes[id(s)] = item_id
            else:
                item_id = self.tree_cat.insert(parent, "end", text=name)
                self._fill_cat_tree(item_id, sub)

    def _fill_files_tree(self, parent, node) -> None:
        if isinstance(node, dict):
            for name, sub in sorted(node.items(), key=lambda kv: kv[0].lower()):
                item_id = self.tree_files.insert(parent, "end", text=f"📁 {name}")
                self._fill_files_tree(item_id, sub)
        elif isinstance(node, list):
            for s in sorted(node, key=lambda x: x.display_key.lower()):
                text = f"📄 § {s.display_key}"
                item_id = self.tree_files.insert(parent, "end", text=text)
                self.section_to_file_nodes[id(s)] = item_id

    def _on_search(self) -> None:
        query = self.entry_query.get().strip()
        if not query:
            messagebox.showinfo("Поиск", "Введите ключ для поиска.")
            return
        self.search_and_open(query)

    def search_and_open(self, query: str) -> None:
        exact, candidates = search_sections(self.sections, query)
        if exact:
            self._open_section(exact, add_to_history=True)
            self.entry_query.delete(0, tk.END)
            self.entry_query.insert(0, exact.display_key)
            return
        if not candidates:
            messagebox.showinfo("Поиск", "Ничего не найдено.")
            return
        self._choose_candidate_and_open(candidates)

    def _choose_candidate_and_open(self, candidates: List[Section]) -> None:
        win = tk.Toplevel(self.root)
        win.title("Выберите раздел")
        win.geometry("500x360")

        lst = tk.Listbox(win)
        lst.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        for s in candidates:
            lst.insert(tk.END, f"{s.display_key}  —  {s.rel_path}")

        def on_ok(*_):
            idx = lst.curselection()
            if not idx:
                return
            s = candidates[idx[0]]
            self._open_section(s, add_to_history=True)
            self.entry_query.delete(0, tk.END)
            self.entry_query.insert(0, s.display_key)
            win.destroy()

        btn_row = ttk.Frame(win, padding=6)
        btn_row.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(btn_row, text="Открыть", command=on_ok).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="Отмена", command=win.destroy).pack(side=tk.RIGHT, padx=(0, 6))

        lst.bind("<Double-Button-1>", on_ok)

    def _open_section(self, s: Section, add_to_history: bool = False) -> None:
        self.current = s
        if add_to_history:
            if self.history_pos < len(self.history) - 1:
                self.history = self.history[: self.history_pos + 1]
            self.history.append(s)
            self.history_pos = len(self.history) - 1

        self.txt_md.delete("1.0", tk.END)
        self.txt_md.insert("1.0", f"## {s.display_key}\n\n{s.markdown}")

        if s.code_blocks:
            self.combo_codes["values"] = [f"{i+1}. ```{cb.lang or 'text'}```" for i, cb in enumerate(s.code_blocks)]
            self.combo_codes.current(0)
            self._show_selected_code()
        else:
            self.combo_codes["values"] = []
            self.combo_codes.set("")
            self.txt_code.delete("1.0", tk.END)

        self._update_nav_buttons()

    def _show_selected_code(self) -> None:
        s = self.current
        if not s or not s.code_blocks:
            return
        idx = self.combo_codes.current()
        if idx < 0:
            idx = 0
        self.txt_code.delete("1.0", tk.END)
        self.txt_code.insert("1.0", s.code_blocks[idx].code)

    def _copy_markdown(self) -> None:
        s = self.current
        if not s:
            return
        to_clipboard(self.root, f"## {s.display_key}\n\n{s.markdown}".strip())

    def _copy_code(self) -> None:
        s = self.current
        if not s or not s.code_blocks:
            return
        idx = self.combo_codes.current()
        if idx < 0:
            idx = 0
        to_clipboard(self.root, s.code_blocks[idx].code)

    def _open_file(self) -> None:
        s = self.current
        if not s:
            return
        open_in_system(s.file_path)

    def _find_in_trees(self) -> None:
        s = self.current
        if not s:
            return
        item_cat = self.section_to_cat_nodes.get(id(s))
        if item_cat:
            self.tree_cat.see(item_cat)
            self.tree_cat.selection_set(item_cat)
        item_file = self.section_to_file_nodes.get(id(s))
        if item_file:
            self.tree_files.see(item_file)
            self.tree_files.selection_set(item_file)

    def _on_cat_double_click(self, _event=None) -> None:
        item = self.tree_cat.selection()
        if not item:
            return
        text = self.tree_cat.item(item[0], "text")
        if text.startswith("§ "):
            name = text[2:]
            if " (" in name:
                name = name.split(" (", 1)[0].strip()
            for s in self.sections:
                if s.display_key == name:
                    self._open_section(s, add_to_history=True)
                    self.entry_query.delete(0, tk.END)
                    self.entry_query.insert(0, s.display_key)
                    break

    def _on_files_double_click(self, _event=None) -> None:
        item = self.tree_files.selection()
        if not item:
            return
        text = self.tree_files.item(item[0], "text")
        if text.startswith("📄 § "):
            name = text.replace("📄 § ", "", 1).strip()
            for s in self.sections:
                if s.display_key == name:
                    self._open_section(s, add_to_history=True)
                    self.entry_query.delete(0, tk.END)
                    self.entry_query.insert(0, s.display_key)
                    break

    def _go_back(self) -> None:
        if self.history_pos > 0:
            self.history_pos -= 1
            s = self.history[self.history_pos]
            self._open_section(s, add_to_history=False)
            self.entry_query.delete(0, tk.END)
            self.entry_query.insert(0, s.display_key)
        self._update_nav_buttons()

    def _go_forward(self) -> None:
        if self.history_pos < len(self.history) - 1:
            self.history_pos += 1
            s = self.history[self.history_pos]
            self._open_section(s, add_to_history=False)
            self.entry_query.delete(0, tk.END)
            self.entry_query.insert(0, s.display_key)
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        self.btn_back.state(["!disabled"] if self.history_pos > 0 else ["disabled"])
        self.btn_forward.state(["!disabled"] if self.history_pos < len(self.history) - 1 else ["disabled"])

# =======================
# 9) MAIN
# =======================

def main() -> None:
    docs_root = os.environ.get("CONTEXT_DOCS_ROOT", DEFAULT_DOCS_ROOT)
    root = tk.Tk()
    if not os.path.isdir(docs_root):
        messagebox.showwarning(
            "Внимание",
            f"Папка docs не найдена.\nОжидалось: {docs_root}\nСоздайте её и добавьте .md файлы."
        )
    sections = load_all_sections(docs_root)
    app = App_UI(root, sections, docs_root, initial_query=(sys.argv[1] if len(sys.argv) > 1 else ""))
    root.mainloop()

if __name__ == "__main__":
    main()
