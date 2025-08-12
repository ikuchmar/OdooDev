#!/usr/bin/env python3
import sys
import re
import difflib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from pathlib import Path

IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}
DOCS_ROOT = Path(__file__).parent.parent / "docs"

class Section:
    def __init__(self, key, categories, markdown, codes, file_path):
        self.key = key
        self.categories = categories
        self.markdown = markdown
        self.codes = codes
        self.file_path = file_path

def parse_md(file_path):
    sections = []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("## "):
            key = lines[i][3:].strip()
            i += 1
            # пропускаем разделители и пустые
            while i < len(lines) and (not lines[i].strip() or re.match(r"^(=|-){3,}$", lines[i].strip())):
                i += 1
            if i >= len(lines):
                break
            categories = lines[i].strip()
            i += 1
            # пропускаем разделители после категорий
            while i < len(lines) and (not lines[i].strip() or re.match(r"^(=|-){3,}$", lines[i].strip())):
                i += 1
            content_lines = []
            codes = []
            current_code = None
            while i < len(lines) and not lines[i].startswith("## "):
                line = lines[i]
                if line.startswith("```"):
                    if current_code is None:
                        current_code = []
                    else:
                        codes.append("\n".join(current_code))
                        current_code = None
                else:
                    if current_code is not None:
                        current_code.append(line)
                    content_lines.append(line)
                i += 1
            markdown = f"## {key}\n" + "\n".join(content_lines).strip()
            sections.append(Section(key, categories, markdown, codes, file_path))
        else:
            i += 1
    return sections

def load_all_sections():
    sections = []
    for path in DOCS_ROOT.rglob("*.md"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        sections.extend(parse_md(path))
    return sections

class App:
    def __init__(self, root, sections, initial_term):
        self.root = root
        self.sections = sections
        self.initial_term = initial_term
        self.history = []
        self.history_index = -1
        self.current_section = None
        self.build_ui()
        if self.initial_term:
            self.search_var.set(self.initial_term)
            self.do_search()

    def build_ui(self):
        self.root.title("Context Docs")
        self.root.geometry("1200x700")

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x")
        tk.Label(top_frame, text="Поиск по ключу:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(top_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True)
        tk.Button(top_frame, text="◀", command=self.go_back).pack(side="left")
        tk.Button(top_frame, text="▶", command=self.go_forward).pack(side="left")
        tk.Button(top_frame, text="Искать", command=self.do_search).pack(side="left")
        tk.Button(top_frame, text="Найти в дереве", command=self.focus_current_in_trees).pack(side="left")

        main_frame = tk.PanedWindow(self.root, orient="horizontal")
        main_frame.pack(fill="both", expand=True)

        # Левый блок с вкладками
        self.notebook = ttk.Notebook(main_frame)
        self.tree_categories = ttk.Treeview(self.notebook)
        self.tree_files = ttk.Treeview(self.notebook)
        self.tree_categories.bind("<Double-1>", lambda e: self.on_tree_open(self.tree_categories, "cat"))
        self.tree_files.bind("<Double-1>", lambda e: self.on_tree_open(self.tree_files, "file"))
        self.notebook.add(self.tree_categories, text="Категории")
        self.notebook.add(self.tree_files, text="Файлы")
        main_frame.add(self.notebook, width=350)

        # Правый блок
        right_frame = tk.Frame(main_frame)
        main_frame.add(right_frame)

        self.markdown_view = ScrolledText(right_frame, wrap="word", height=20)
        self.markdown_view.pack(fill="both", expand=True)
        self.markdown_view.config(state="disabled")

        code_frame = tk.Frame(right_frame)
        code_frame.pack(fill="both", expand=True)
        self.code_var = tk.StringVar()
        self.code_combo = ttk.Combobox(code_frame, textvariable=self.code_var, state="readonly")
        self.code_combo.pack(fill="x")
        self.code_combo.bind("<<ComboboxSelected>>", self.update_code_view)

        self.code_view = ScrolledText(code_frame, wrap="none", height=10)
        self.code_view.pack(fill="both", expand=True)
        self.code_view.config(state="disabled")

        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="Скопировать весь блок", command=self.copy_all).pack(side="left")
        tk.Button(btn_frame, text="Скопировать код", command=self.copy_code).pack(side="left")
        tk.Button(btn_frame, text="Открыть .md", command=self.open_md).pack(side="left")
        tk.Button(btn_frame, text="Закрыть", command=self.root.destroy).pack(side="right")

        self.build_trees()

    def build_trees(self):
        # Категории
        cat_dict = {}
        for s in self.sections:
            parts = [p.strip() for p in s.categories.split(" - ")]
            d = cat_dict
            for part in parts:
                d = d.setdefault(part, {})
            d.setdefault("__sections__", []).append(s)

        def insert_nodes(tree, parent, struct):
            for k, v in struct.items():
                if k == "__sections__":
                    for sec in v:
                        tree.insert(parent, "end", iid=f"sec::{sec.key}::{sec.file_path}", text=f"§ {sec.key}")
                else:
                    node_id = tree.insert(parent, "end", text=k)
                    insert_nodes(tree, node_id, v)

        self.tree_categories.delete(*self.tree_categories.get_children())
        insert_nodes(self.tree_categories, "", cat_dict)

        # Файлы
        file_dict = {}
        for s in self.sections:
            rel = s.file_path.relative_to(DOCS_ROOT)
            parts = rel.parts
            d = file_dict
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d.setdefault(parts[-1], []).append(s)

        def insert_file_nodes(tree, parent, struct):
            for k, v in struct.items():
                if isinstance(v, list):
                    node_id = tree.insert(parent, "end", text=k)
                    for sec in v:
                        tree.insert(node_id, "end", iid=f"sec::{sec.key}::{sec.file_path}", text=f"§ {sec.key}")
                else:
                    node_id = tree.insert(parent, "end", text=k)
                    insert_file_nodes(tree, node_id, v)

        self.tree_files.delete(*self.tree_files.get_children())
        insert_file_nodes(self.tree_files, "", file_dict)

    def on_tree_open(self, tree, mode):
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("sec::"):
            _, key, file_path = iid.split("::", 2)
            for s in self.sections:
                if s.key == key and str(s.file_path) == file_path:
                    self.open_section(s, add_history=True)

    def do_search(self):
        term = self.search_var.get().strip().lower()
        if not term:
            return
        keys = [s.key.lower() for s in self.sections]
        if term in keys:
            idx = keys.index(term)
        else:
            match = difflib.get_close_matches(term, keys, n=1)
            if not match:
                messagebox.showinfo("Поиск", "Ничего не найдено")
                return
            idx = keys.index(match[0])
        self.open_section(self.sections[idx], add_history=True)

    def open_section(self, section, add_history=False):
        self.current_section = section
        if add_history:
            self.history = self.history[:self.history_index+1]
            self.history.append(section)
            self.history_index += 1
        self.markdown_view.config(state="normal")
        self.markdown_view.delete("1.0", "end")
        self.markdown_view.insert("1.0", section.markdown)
        self.markdown_view.config(state="disabled")
        if section.codes:
            self.code_combo["values"] = [f"Блок {i+1}" for i in range(len(section.codes))]
            self.code_combo.current(0)
        else:
            self.code_combo["values"] = ["— нет кода —"]
            self.code_combo.current(0)
        self.update_code_view()

    def update_code_view(self, event=None):
        self.code_view.config(state="normal")
        self.code_view.delete("1.0", "end")
        if self.current_section and self.current_section.codes and self.code_combo.current() >= 0:
            idx = self.code_combo.current()
            if idx < len(self.current_section.codes):
                self.code_view.insert("1.0", self.current_section.codes[idx])
        self.code_view.config(state="disabled")

    def copy_all(self):
        if self.current_section:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_section.markdown)

    def copy_code(self):
        if self.current_section and self.current_section.codes:
            idx = self.code_combo.current()
            if idx < len(self.current_section.codes):
                self.root.clipboard_clear()
                self.root.clipboard_append(self.current_section.codes[idx])

    def open_md(self):
        if self.current_section:
            path = self.current_section.file_path
            if path.exists():
                import webbrowser
                webbrowser.open(str(path))

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.open_section(self.history[self.history_index], add_history=False)

    def go_forward(self):
        if self.history_index < len(self.history)-1:
            self.history_index += 1
            self.open_section(self.history[self.history_index], add_history=False)

    def focus_current_in_trees(self):
        if not self.current_section:
            return
        target_iid = f"sec::{self.current_section.key}::{self.current_section.file_path}"
        for tree in (self.tree_categories, self.tree_files):
            def find_and_focus(parent=""):
                for iid in tree.get_children(parent):
                    if iid == target_iid:
                        tree.see(iid)
                        tree.selection_set(iid)
                        return True
                    if find_and_focus(iid):
                        tree.item(iid, open=True)
                        return True
                return False
            find_and_focus()

if __name__ == "__main__":
    initial_term = sys.argv[1] if len(sys.argv) > 1 else ""
    sections = load_all_sections()
    root = tk.Tk()
    app = App(root, sections, initial_term)
    root.mainloop()
