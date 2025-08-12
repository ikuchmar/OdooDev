import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from pathlib import Path
from difflib import get_close_matches
import webbrowser
import re

# === Настройки ===
DOCS_ROOT = Path(__file__).parent.parent / "docs"
IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}
CATEGORY_SEP = " - "                               # разделитель уровней в линии иерархии
SEP_LINE_RE = re.compile(r"^\s*[=\-]{3,}\s*$")     # ===== / ----- (необязательные, любая длина)

# === Обход и парсинг ===
def iter_markdown_files(root: Path):
    for p in root.rglob("*.md"):
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        yield p

def parse_markdown_sections(md_path: Path):
    """
    Секция в .md:
      (опц) =====
      ## ключ
      (опц) =====
      (опц) пустые строки
      (опц) Кат1 - Кат2 - Кат3
      (опц) -----
      далее markdown до следующего '## '
      код-блоки в ```...```

    Возвращает список:
      {
        "key": str,           # ключ (lower)
        "full": str,          # полный markdown секции (включая строку "## ключ", но без строки иерархии)
        "codes": [str, ...],  # все код-блоки (без тройных бэктиков)
        "cats": [str, ...]    # путь категорий
      }
    """
    lines = md_path.read_text(encoding="utf-8").splitlines(True)

    sections = []
    key = None
    buf = []
    in_code = False
    code_buf = []
    codes = []
    awaiting_hierarchy = False
    cats = []

    def flush():
        nonlocal sections, key, buf, codes, cats
        if key:
            full = "".join(buf).strip()
            sections.append({"key": key, "full": full, "codes": codes[:], "cats": cats})
        buf.clear()
        codes = []
        cats = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Разделительные линии вне кода игнорируем
        if not in_code and SEP_LINE_RE.match(line):
            i += 1
            continue

        # Начало новой секции
        if not in_code and line.startswith("## "):
            # закрыть предыдущую секцию
            if code_buf:
                codes.append("".join(code_buf))
                code_buf = []
            flush()
            key = line[3:].strip().lower()
            awaiting_hierarchy = True
            buf = [line]  # заголовок включаем в full
            i += 1
            continue

        if key:
            # строка иерархии (первая непустая/не-разделительная после заголовка)
            if awaiting_hierarchy:
                if line.strip() == "" or SEP_LINE_RE.match(line):
                    i += 1
                    continue
                cats = [c.strip() for c in line.strip().split(CATEGORY_SEP) if c.strip()]
                awaiting_hierarchy = False
                # следующая строка может быть разделителем — пропустим
                i += 1
                if i < n and SEP_LINE_RE.match(lines[i]):
                    i += 1
                continue

            # код-блоки
            if line.strip().startswith("```") and not in_code:
                in_code = True
                code_buf = []
                buf.append(line)
                i += 1
                continue
            elif line.strip().startswith("```") and in_code:
                in_code = False
                codes.append("".join(code_buf))
                buf.append(line)
                code_buf = []
                i += 1
                continue

            if in_code:
                code_buf.append(line)
                buf.append(line)
                i += 1
                continue

            # обычный текст секции
            buf.append(line)
            i += 1
            continue

        # вне секции
        i += 1

    # хвост
    if in_code and code_buf:
        codes.append("".join(code_buf))
    flush()
    return sections

def build_indexes(root: Path):
    """
    Возвращает:
      flat_sections: dict[str, list[payload]]
      files_tree: {dir:{...,"__files__":{Path:[sections]}}}
      cats_tree: дерево по категориям (из строки после заголовка)
    payload = {"full","codes","src","title","cats","key"}
    """
    flat_sections = {}
    files_tree = {}
    cats_tree = {}

    def ensure_path(tree, parts):
        node = tree
        for p in parts:
            node = node.setdefault(p, {})
        return node

    for md in iter_markdown_files(root):
        rel = md.relative_to(root)

        # дерево по файлам
        node = ensure_path(files_tree, list(rel.parts[:-1]))
        files_node = node.setdefault("__files__", {})
        secs = parse_markdown_sections(md)
        files_node[md] = secs

        # индексация и дерево категорий
        for s in secs:
            k = s["key"]
            first_line = (s["full"].splitlines() or [f"## {k}"])[0]
            title = first_line.replace("##", "", 1).strip() or k

            payload = {"full": s["full"], "codes": s["codes"], "src": md, "title": title, "cats": s["cats"], "key": k}
            flat_sections.setdefault(k, []).append(payload)

            cat_node = cats_tree
            for c in s["cats"]:
                cat_node = cat_node.setdefault(c, {})
            lst = cat_node.setdefault("__sections__", [])
            lst.append(payload)

    return flat_sections, files_tree, cats_tree

# === UI helpers ===
def copy_to_clipboard(root_win: tk.Tk, text: str):
    if text is None:
        text = ""
    root_win.clipboard_clear()
    root_win.clipboard_append(text)
    root_win.update()

def open_in_browser(path: Path):
    webbrowser.open(path.as_uri())

def tree_find_and_focus(tree: ttk.Treeview, predicate):
    """Найти первый узел по предикату(values) и сфокусировать/прокрутить."""
    def walk(item=""):
        for child in tree.get_children(item):
            vals = tree.item(child, "values")
            if predicate(vals):
                tree.selection_set(child)
                tree.focus(child)
                tree.see(child)
                return True
            if walk(child):
                return True
        return False
    walk("")

# === Приложение ===
def run_app(initial_term: str):
    if not DOCS_ROOT.exists():
        messagebox.showerror("Ошибка", f"Папка {DOCS_ROOT} не найдена.")
        return

    flat_sections, files_tree, cats_tree = build_indexes(DOCS_ROOT)

    # Текущий документ + история
    current_doc = {}     # {"full","codes","src","title","key"}
    history = []         # [(src_path, key_lower, title)]
    hist_idx = -1
    _nav_lock = False    # чтобы назад/вперёд не добавляло в историю

    root = tk.Tk()
    root.title("Документация")
    root.geometry("1150x750")
    root.minsize(950, 620)

    # --- Верх: поиск + история + «найти в дереве» ---
    top = tk.Frame(root)
    top.pack(fill="x", padx=8, pady=6)

    tk.Label(top, text="Поиск по ключу:").pack(side="left")
    search_entry = tk.Entry(top, width=40)
    search_entry.pack(side="left", fill="x", expand=True, padx=6)
    search_entry.insert(0, initial_term)

    def update_hist_buttons():
        btn_back.configure(state=("normal" if hist_idx > 0 else "disabled"))
        btn_fwd.configure(state=("normal" if 0 <= hist_idx < len(history)-1 else "disabled"))

    def push_history(src: Path, key: str, title: str):
        nonlocal hist_idx
        if hist_idx < len(history)-1:
            del history[hist_idx+1:]
        history.append((src, key, title))
        hist_idx = len(history)-1
        update_hist_buttons()

    def go_history(delta: int):
        nonlocal hist_idx, _nav_lock
        new_idx = hist_idx + delta
        if not (0 <= new_idx < len(history)):
            return
        hist_idx = new_idx
        update_hist_buttons()
        src, key, title = history[hist_idx]
        _nav_lock = True
        open_doc_by_path_key(src, key, title_override=title)
        _nav_lock = False

    btn_back = tk.Button(top, text="◀", width=3, command=lambda: go_history(-1))
    btn_back.pack(side="left")
    btn_fwd = tk.Button(top, text="▶", width=3, command=lambda: go_history(+1))
    btn_fwd.pack(side="left", padx=(2, 8))
    btn_pos = tk.Button(top, text="Найти в дереве", command=lambda: focus_current_in_trees())
    btn_pos.pack(side="left")

    def do_search():
        term = search_entry.get().strip()
        if not term:
            return
        key = term.lower()
        variants = flat_sections.get(key)
        title = term
        hit = None
        if not variants:
            keys = list(flat_sections.keys())
            close = get_close_matches(key, keys, n=1)
            if close:
                variants = flat_sections[close[0]]
                title = f"Похожее: {close[0]}"
        if variants:
            hit = variants[0]  # если ключ в нескольких файлах — берём первый
        if not hit:
            messagebox.showinfo("Нет описания", f"Нет описания для: {term}")
            return
        open_doc(hit, key=key, title_override=title)

    tk.Button(top, text="Искать", command=do_search).pack(side="left", padx=6)

    # --- Центр: слева навигация, справа контент ---
    main = tk.PanedWindow(root, sashrelief="raised", sashwidth=5)
    main.pack(fill="both", expand=True)

    # Левая панель с вкладками
    left = tk.Frame(main)
    main.add(left, minsize=320)

    nb = ttk.Notebook(left)
    nb.pack(fill="both", expand=True, padx=6, pady=6)

    tree_cats = ttk.Treeview(nb, show="tree")
    nb.add(tree_cats, text="Категории")

    tree_files = ttk.Treeview(nb, show="tree")
    nb.add(tree_files, text="Файлы")

    # Правая панель: верх — полный блок, низ — отдельный код
    right = tk.Frame(main)
    main.add(right)

    text_box = scrolledtext.ScrolledText(right, wrap="word", height=18)
    text_box.pack(fill="both", expand=True, padx=6, pady=(6,3))
    text_box.configure(state="disabled")

    code_panel = tk.Frame(right)
    code_panel.pack(fill="both", expand=False, padx=6, pady=(0,6))

    code_header = tk.Frame(code_panel)
    code_header.pack(fill="x")

    tk.Label(code_header, text="Код‑блок:").pack(side="left")

    code_selector = ttk.Combobox(code_header, state="readonly", values=[])
    code_selector.pack(side="left", padx=6)

    def on_select_code(event=None):
        idx = code_selector.current()
        codes = current_doc.get("codes", [])
        snippet = codes[idx] if (0 <= idx < len(codes)) else ""
        code_box.configure(state="normal")
        code_box.delete("1.0", tk.END)
        code_box.insert("1.0", snippet)
        code_box.configure(state="disabled")

    code_selector.bind("<<ComboboxSelected>>", on_select_code)

    code_box = scrolledtext.ScrolledText(code_panel, wrap="none", height=12)
    code_box.configure(state="disabled")
    code_box.pack(fill="both", expand=True, pady=(3,0))

    btn_bar = tk.Frame(right)
    btn_bar.pack(fill="x", padx=6, pady=6)
    btn_copy_all = tk.Button(btn_bar, text="Скопировать весь блок",
                             command=lambda: copy_to_clipboard(root, current_doc.get("full", "")))
    def copy_current_code():
        idx = code_selector.current()
        codes = current_doc.get("codes", [])
        snippet = codes[idx] if (0 <= idx < len(codes)) else ""
        copy_to_clipboard(root, snippet)
    btn_copy_code = tk.Button(btn_bar, text="Скопировать код", command=copy_current_code)
    btn_open = tk.Button(btn_bar, text="Открыть .md",
                         command=lambda: open_in_browser(current_doc["src"]) if "src" in current_doc else None)
    btn_close = tk.Button(btn_bar, text="Закрыть", command=root.destroy)
    btn_copy_all.pack(side="left", padx=4)
    btn_copy_code.pack(side="left", padx=4)
    btn_open.pack(side="left", padx=4)
    btn_close.pack(side="right", padx=4)

    # --- Заполнение дерева Файлы ---
    def fill_files_tree():
        def add_dir(node_id, subtree):
            for name, sub in sorted((k, v) for k, v in subtree.items() if k != "__files__"):
                child_id = tree_files.insert(node_id, "end", text=f"📁 {name}", open=False)
                add_dir(child_id, sub)
            files = subtree.get("__files__", {})
            for md_path, sections in sorted(files.items(), key=lambda kv: kv[0].name.lower()):
                file_id = tree_files.insert(node_id, "end", text=f"📄 {md_path.name}", open=False, values=(str(md_path), "file"))
                for s in sections:
                    first_line = (s["full"].splitlines() or [f"## {s['key']}"])[0]
                    title = first_line.replace("##", "", 1).strip() or s["key"]
                    tree_files.insert(file_id, "end", text=f"§ {title}", values=(str(md_path), "section", s["key"]))
        root_id = tree_files.insert("", "end", text=f"📚 {DOCS_ROOT.name}", open=True)
        add_dir(root_id, files_tree)

    # --- Заполнение дерева Категории (без верхнего узла) ---
    def fill_cats_tree():
        def add_cat(node_id, subtree):
            for name, sub in sorted((k, v) for k, v in subtree.items() if k != "__sections__"):
                child = tree_cats.insert(node_id, "end", text=f"🏷️ {name}", open=False)
                add_cat(child, sub)
            for sec in subtree.get("__sections__", []):
                md_path = sec["src"]
                title = sec.get("title") or sec["key"]
                tree_cats.insert(node_id, "end", text=f"§ {title}", values=(str(md_path), "section", sec["key"]))
        add_cat("", cats_tree)

    fill_files_tree()
    fill_cats_tree()

    # --- Показ документа и история ---
    def extract_key_from_full(full: str) -> str:
        for line in full.splitlines():
            if line.startswith("## "):
                return line[3:].strip().lower()
        return ""

    def show_doc(payload, title_override=None, key=None, add_to_history=True):
        nonlocal _nav_lock
        full = payload["full"]
        codes = payload.get("codes", [])
        src = payload["src"]
        t = title_override or payload.get("title") or ""
        k = (key or payload.get("key") or extract_key_from_full(full) or "").lower()

        current_doc.clear()
        current_doc.update({"full": full, "codes": codes, "src": src, "title": t, "key": k})

        root.title(f"Документация — {t} — {src.relative_to(DOCS_ROOT)}")

        # Полный блок
        text_box.configure(state="normal")
        text_box.delete("1.0", tk.END)
        text_box.insert("1.0", full)
        text_box.configure(state="disabled")

        # Код‑блоки
        code_selector["values"] = [f"Блок {i+1}" for i in range(len(codes))] or ["— нет кода —"]
        code_selector.current(0 if codes else 0)
        on_select_code()

        if add_to_history and not _nav_lock:
            push_history(src, k, t)

    def open_doc(hit, key=None, title_override=None):
        show_doc(hit, title_override=title_override, key=key, add_to_history=True)

    def open_doc_by_path_key(src: Path, key: str, title_override=None):
        for s in parse_markdown_sections(src):
            if s["key"] == key:
                first_line = (s["full"].splitlines() or [f"## {key}"])[0]
                title = first_line.replace("##", "", 1).strip() or key
                show_doc({"full": s["full"], "codes": s["codes"], "src": src, "title": title, "key": key},
                         title_override or title, key=key, add_to_history=False)
                return True
        return False

    # --- Позиционирование деревьев на текущий ключ ---
    def focus_current_in_trees():
        if "src" not in current_doc or "key" not in current_doc:
            return
        src = current_doc["src"]
        key = current_doc["key"]

        def match_vals(vals):
            if not vals:
                return False
            kind = vals[1] if len(vals) > 1 else ""
            v_path = vals[0] if len(vals) > 0 else ""
            v_key = vals[2] if len(vals) > 2 else ""
            return (kind == "section" and Path(v_path) == src and (v_key or "").lower() == key)

        tree_find_and_focus(tree_files, match_vals)
        tree_find_and_focus(tree_cats, match_vals)

    # --- Обработчики деревьев ---
    def on_tree_activate(tree):
        sel = tree.focus()
        if not sel:
            return
        vals = tree.item(sel, "values")
        if not vals:
            return
        kind = vals[1] if len(vals) > 1 else ""
        if kind == "section":
            md_path = Path(vals[0])
            key = (vals[2] or "").lower()
            for s in parse_markdown_sections(md_path):
                if s["key"] == key:
                    first_line = (s["full"].splitlines() or [f"## {key}"])[0]
                    title = first_line.replace("##", "", 1).strip() or key
                    show_doc({"full": s["full"], "codes": s["codes"], "src": md_path, "title": title, "key": key},
                             title_override=title, key=key, add_to_history=True)
                    break

    tree_files.bind("<Double-1>", lambda e: on_tree_activate(tree_files))
    tree_files.bind("<Return>",  lambda e: on_tree_activate(tree_files))
    tree_cats.bind("<Double-1>", lambda e: on_tree_activate(tree_cats))
    tree_cats.bind("<Return>",  lambda e: on_tree_activate(tree_cats))

    # авто-поиск при открытии
    if initial_term:
        do_search()
    update_hist_buttons()

    root.mainloop()

# === Точка входа ===
if __name__ == "__main__":
    initial = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    run_app(initial)
