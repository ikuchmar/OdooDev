#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Утилита: Просмотр полей Odoo в древовидной структуре (GUI на tkinter).

Запуск:
    python script.py [<фильтр>]

Где <фильтр> — необязательная подстрока (без регистра), применяется к модулям/моделям/полям.

Файл со списком модулей:
    modules_list.txt — по одному пути к корню модуля в строке.
    Пример:
        /home/user/odoo/custom/addons/sale
        /home/user/odoo/custom/addons/stock

Особенности:
    - Статический разбор Python-файлов в папке models/ через ast (без запуска Odoo).
    - Извлекаются: _name, _inherit, _inherits и поля вида: <attr> = fields.<Тип>(...).
    - Python 3.8+, без внешних зависимостей.
"""

# ==========================
# БЛОК 1. ИМПОРТЫ И КОНСТАНТЫ
# ==========================

import ast
import os
import sys
import traceback
from dataclasses import dataclass, field as dc_field
from typing import List, Dict, Optional, Union

# Имя файла со списком путей к модулям
MODULES_LIST_FILE = "modules_list.txt"

# Подкаталог, в котором обычно лежат модели модуля
DEFAULT_MODELS_DIR_NAME = "models"

# Эвристика для определения "класса‑модели" Odoo:
# базовый класс называется "Model" (обычно: models.Model)
MODEL_BASE_CLASS_CANDIDATES = {"Model"}


# ==========================
# БЛОК 2. СТРУКТУРЫ ДАННЫХ
# ==========================

@dataclass
class FieldInfo:
    """Информация о поле модели Odoo."""
    name: str                 # имя атрибута в классе (имя поля)
    ftype: str                # тип поля (Char, Many2one, Float, ...)
    args_preview: str = ""    # короткое превью аргументов вызова

@dataclass
class ModelInfo:
    """Информация о модели Odoo (класс, унаследованный от models.Model)."""
    class_name: str
    model_name: Optional[str] = None
    inherit: Optional[Union[str, List[str]]] = None
    inherits: Optional[Dict[str, str]] = None
    fields: List[FieldInfo] = dc_field(default_factory=list)
    file_path: Optional[str] = None

@dataclass
class ModuleInfo:
    """Информация о модуле (папка)."""
    name: str
    path: str
    models: List[ModelInfo] = dc_field(default_factory=list)


# ==========================
# БЛОК 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ AST
# ==========================

def read_modules_list(list_path: str) -> List[str]:
    """
    Читает файл со списком путей к модулям.
    Пустые строки и комментарии (#...) игнорируются.
    Возвращает список существующих директорий.
    """
    paths: List[str] = []
    if not os.path.exists(list_path):
        print(f"[ВНИМАНИЕ] Файл не найден: {list_path}")
        return paths

    with open(list_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            abspath = os.path.abspath(os.path.expanduser(line))
            if os.path.isdir(abspath):
                paths.append(abspath)
            else:
                print(f"[ПРЕДУПРЕЖДЕНИЕ] Путь не существует: {abspath}")
    return paths


def find_model_files(module_path: str) -> List[str]:
    """
    Ищет Python-файлы моделей в подкаталоге 'models' указанного модуля.
    Возвращает список путей к .py файлам (кроме файлов, начинающихся с '_').
    """
    model_dir = os.path.join(module_path, DEFAULT_MODELS_DIR_NAME)
    result: List[str] = []
    if not os.path.isdir(model_dir):
        return result
    for root, _, files in os.walk(model_dir):
        for name in files:
            if name.endswith(".py") and not name.startswith("_"):
                result.append(os.path.join(root, name))
    return result


def safe_get_id(node: ast.AST) -> Optional[str]:
    """
    Пытается получить идентификатор (имя) из узла AST (Name или Attribute).
    Для базового класса: models.Model -> 'Model'; Name('Model') -> 'Model'.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def is_fields_call(node: ast.AST) -> Optional[str]:
    """
    Проверяет, является ли узел вызовом вида fields.<Тип>(...).
    Возвращает имя типа поля (например, 'Char', 'Many2one') либо None.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute):
        base = func.value
        if isinstance(base, ast.Name) and base.id == "fields":
            return func.attr
    return None


def _fallback_unparse(node: ast.AST) -> str:
    """
    Упрощённый "unparse" для Python 3.8 (где нет ast.unparse).
    Достаточно для компактного превью аргументов.
    """
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Str):
        return repr(node.s)
    if isinstance(node, ast.Num):
        return repr(node.n)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_fallback_unparse(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        fn = _fallback_unparse(node.func)
        args = ", ".join(_fallback_unparse(a) for a in node.args)
        return f"{fn}({args})"
    if isinstance(node, ast.List):
        return "[" + ", ".join(_fallback_unparse(e) for e in node.elts) + "]"
    if isinstance(node, ast.Dict):
        pairs = []
        for k, v in zip(node.keys, node.values):
            pairs.append(f"{_fallback_unparse(k)}: {_fallback_unparse(v)}")
        return "{" + ", ".join(pairs) + "}"
    return "<expr>"


def unparse_expr(node: ast.AST) -> str:
    """
    Возвращает строковое представление выражения.
    На Python 3.9+ использует ast.unparse, на 3.8 — упрощённый фолбэк.
    """
    if hasattr(ast, "unparse"):
        try:
            return ast.unparse(node)
        except Exception:
            return _fallback_unparse(node)
    return _fallback_unparse(node)


def extract_call_args_preview(call: ast.Call, max_len: int = 140) -> str:
    """
    Собирает компактную строку с аргументами вызова: позиционные и именованные.
    """
    parts: List[str] = []
    for arg in call.args:
        parts.append(unparse_expr(arg))
    for kw in call.keywords:
        key = kw.arg if kw.arg is not None else "**"
        parts.append(f"{key}={unparse_expr(kw.value)}")
    s = "(" + ", ".join(parts) + ")"
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def literal_or_expr(node: Optional[ast.AST]) -> Optional[Union[str, Dict[str, str], List[str]]]:
    """
    Пытается извлечь "простое" значение Python для _name / _inherit / _inherits:
      - строку,
      - список строк,
      - словарь {str: str}.
    Если не получилось — вернёт строковое представление выражения (подсказка).
    """
    if node is None:
        return None
    try:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Str):
            return node.s
        if isinstance(node, ast.List):
            items: List[str] = []
            for elt in node.elts:
                if isinstance(elt, (ast.Constant, ast.Str)) and isinstance(getattr(elt, "value", getattr(elt, "s", None)), str):
                    items.append(getattr(elt, "value", getattr(elt, "s", "")))
                else:
                    items.append(unparse_expr(elt))
            return items
        if isinstance(node, ast.Dict):
            d: Dict[str, str] = {}
            for k, v in zip(node.keys, node.values):
                key = None
                val = None
                if isinstance(k, (ast.Constant, ast.Str)) and isinstance(getattr(k, "value", getattr(k, "s", None)), str):
                    key = getattr(k, "value", getattr(k, "s", None))
                else:
                    key = unparse_expr(k)
                if isinstance(v, (ast.Constant, ast.Str)) and isinstance(getattr(v, "value", getattr(v, "s", None)), str):
                    val = getattr(v, "value", getattr(v, "s", None))
                else:
                    val = unparse_expr(v)
                d[str(key)] = str(val)
            return d
        return unparse_expr(node)
    except Exception:
        return None


def class_inherits_models_model(node: ast.ClassDef) -> bool:
    """
    Эвристика: класс — модель Odoo, если среди баз есть 'Model'
    (например: class X(models.Model): ...).
    """
    for base in node.bases:
        base_name = safe_get_id(base)
        if base_name in MODEL_BASE_CLASS_CANDIDATES:
            return True
    return False


def parse_models_from_file(py_path: str) -> List[ModelInfo]:
    """
    Парсит .py файл и извлекает список ModelInfo.
    """
    try:
        with open(py_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        print(f"[ОШИБКА] Чтение {py_path}: {e}")
        return []

    try:
        tree = ast.parse(source, filename=py_path)
    except Exception as e:
        print(f"[ОШИБКА] AST {py_path}: {e}")
        return []

    models: List[ModelInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not class_inherits_models_model(node):
            continue

        mi = ModelInfo(class_name=node.name, file_path=py_path)

        for stmt in node.body:
            # Присваивания на уровне класса
            if isinstance(stmt, ast.Assign):
                targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
                if not targets:
                    continue

                # Служебные атрибуты
                for t in targets:
                    if t.id in {"_name", "_inherit", "_inherits"}:
                        value = literal_or_expr(stmt.value)
                        if t.id == "_name":
                            mi.model_name = value if isinstance(value, str) else str(value)
                        elif t.id == "_inherit":
                            mi.inherit = value
                        elif t.id == "_inherits":
                            mi.inherits = value if isinstance(value, dict) else None

                # Поля вида: name = fields.Char(...)
                if isinstance(stmt.value, ast.Call):
                    ftype = is_fields_call(stmt.value)
                    if ftype:
                        for t in targets:
                            args_prev = extract_call_args_preview(stmt.value)
                            mi.fields.append(FieldInfo(name=t.id, ftype=ftype, args_preview=args_prev))

            # Аннотированные присваивания: name: X = fields.Char(...)
            if isinstance(stmt, ast.AnnAssign):
                if isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
                    ftype = is_fields_call(stmt.value)
                    if ftype:
                        mi.fields.append(
                            FieldInfo(name=stmt.target.id, ftype=ftype, args_preview=extract_call_args_preview(stmt.value))
                        )

        models.append(mi)

    return models


def build_modules_info(mod_paths: List[str]) -> List[ModuleInfo]:
    """
    Для каждого пути модуля собирает модели/поля.
    """
    result: List[ModuleInfo] = []
    for mod_path in mod_paths:
        module = ModuleInfo(name=os.path.basename(os.path.abspath(mod_path)), path=mod_path)
        for pyf in find_model_files(mod_path):
            module.models.extend(parse_models_from_file(pyf))
        result.append(module)
    return result


def apply_filter(mods: List[ModuleInfo], key: Optional[str]) -> List[ModuleInfo]:
    """
    Подстрочный фильтр (без регистра) по модулю/модели/полю.
    Возвращает НОВУЮ структурe (оригинал не меняется).
    """
    if not key:
        return mods
    k = key.lower()

    filtered: List[ModuleInfo] = []
    for m in mods:
        mod_match = (k in m.name.lower()) or (k in m.path.lower())

        new_models: List[ModelInfo] = []
        for mdl in m.models:
            hay = [
                mdl.class_name or "",
                mdl.model_name or "",
                str(mdl.inherit) if mdl.inherit is not None else "",
                str(mdl.inherits) if mdl.inherits is not None else "",
                mdl.file_path or "",
            ]
            model_match = any(k in s.lower() for s in hay)

            new_fields: List[FieldInfo] = []
            for fld in mdl.fields:
                if any(k in s.lower() for s in (fld.name, fld.ftype, fld.args_preview)):
                    new_fields.append(fld)

            if mod_match or model_match or new_fields:
                mdl_copy = ModelInfo(
                    class_name=mdl.class_name,
                    model_name=mdl.model_name,
                    inherit=mdl.inherit,
                    inherits=mdl.inherits,
                    fields=new_fields if not (mod_match or model_match) else mdl.fields,
                    file_path=mdl.file_path,
                )
                new_models.append(mdl_copy)

        if mod_match or new_models:
            filtered.append(ModuleInfo(name=m.name, path=m.path, models=new_models))

    return filtered


# ==========================
# БЛОК 4. ВЫВОД В КОНСОЛЬ (ФОЛБЭК)
# ==========================

def print_tree_console(mods: List[ModuleInfo]) -> None:
    """
    Печатает дерево в консоль (на случай отсутствия GUI).
    """
    for mod in mods:
        print(f"[{mod.name}]  ({mod.path})")
        for mdl in mod.models:
            model_line = mdl.model_name or mdl.class_name
            extra = []
            if mdl.inherit:
                extra.append(f"_inherit={mdl.inherit}")
            if mdl.inherits:
                extra.append(f"_inherits={mdl.inherits}")
            suffix = ("  {" + ", ".join(extra) + "}") if extra else ""
            print(f"  └─ {model_line}  [{mdl.class_name}]{suffix}")
            for fld in mdl.fields:
                print(f"       • {fld.name}: {fld.ftype} {fld.args_preview}")
        print()


# ==========================
# БЛОК 5. GUI НА TKINTER
# ==========================

def show_gui(mods: List[ModuleInfo], initial_filter: str = "") -> None:
    """
    Показывает простое окно на tkinter: поле фильтра + Treeview.
    Двойной клик по узлу — всплывающее окно с подробностями.
    ПКМ — контекстное меню (копировать строку).
    """
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Odoo Models & Fields Viewer")
    root.geometry("1150x720")

    # -------- Верхняя панель: фильтр --------
    top = ttk.Frame(root, padding=8)
    top.pack(side=tk.TOP, fill=tk.X)

    tk.Label(top, text="Фильтр:").pack(side=tk.LEFT)
    var_key = tk.StringVar(value=initial_filter)
    ent = ttk.Entry(top, textvariable=var_key, width=50)
    ent.pack(side=tk.LEFT, padx=6)

    def apply_filter_and_rebuild():
        key = var_key.get().strip()
        current = apply_filter(mods, key)
        rebuild_tree(current)

    ttk.Button(top, text="Применить", command=apply_filter_and_rebuild).pack(side=tk.LEFT, padx=4)

    # -------- Центральная панель: дерево --------
    center = ttk.Frame(root, padding=(8, 0, 8, 8))
    center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    columns = ("type", "info")
    tree = ttk.Treeview(center, columns=columns, show="tree headings")
    tree.heading("#0", text="Название")
    tree.heading("type", text="Тип")
    tree.heading("info", text="Информация")
    tree.column("#0", width=420)
    tree.column("type", width=120, anchor="w")
    tree.column("info", width=560, anchor="w")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    vsb = ttk.Scrollbar(center, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # -------- Заполнение дерева --------
    def rebuild_tree(current: List[ModuleInfo]):
        tree.delete(*tree.get_children())
        for mod in current:
            mod_id = tree.insert("", "end", text=mod.name, values=("module", mod.path), open=True)
            for mdl in mod.models:
                extras = []
                if mdl.inherit:
                    extras.append(f"_inherit={mdl.inherit}")
                if mdl.inherits:
                    extras.append(f"_inherits={mdl.inherits}")
                info = f"{mdl.class_name} @ {mdl.file_path or ''}"
                if extras:
                    info += "  {" + ", ".join(extras) + "}"
                mdl_id = tree.insert(mod_id, "end", text=(mdl.model_name or mdl.class_name), values=("model", info), open=False)
                for fld in mdl.fields:
                    fld_info = f"{fld.ftype} {fld.args_preview}"
                    tree.insert(mdl_id, "end", text=fld.name, values=("field", fld_info), open=False)

    rebuild_tree(mods)

    # Enter — применить фильтр
    ent.bind("<Return>", lambda e: apply_filter_and_rebuild())

    # -------- Контекстное меню (ПКМ) --------
    menu = tk.Menu(root, tearoff=0)

    def copy_selected_line():
        sel = tree.selection()
        if not sel:
            return
        iid = sel[0]
        text = tree.item(iid, "text")
        vals = tree.item(iid, "values")
        line = f"{text}  {tuple(vals)}"
        root.clipboard_clear()
        root.clipboard_append(line)

    menu.add_command(label="Копировать строку", command=copy_selected_line)

    def on_right_click(evt):
        row = tree.identify_row(evt.y)
        if row:
            tree.selection_set(row)
            menu.tk_popup(evt.x_root, evt.y_root)

    tree.bind("<Button-3>", on_right_click)

    # -------- Подробности по двойному клику --------
    def on_double_click(evt):
        row = tree.selection()
        if not row:
            return
        iid = row[0]
        text = tree.item(iid, "text")
        vals = tree.item(iid, "values")
        detail = f"Название: {text}\nТип: {vals[0] if vals else ''}\nИнфо: {vals[1] if len(vals) > 1 else ''}"

        win = tk.Toplevel(root)
        win.title("Детали")
        win.geometry("700x300")
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        txt = tk.Text(frm, wrap="word")
        txt.insert("1.0", detail)
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)

    tree.bind("<Double-1>", on_double_click)

    # Фокус в фильтр при старте
    root.after(50, lambda: ent.focus_set())

    root.mainloop()


# ==========================
# БЛОК 6. MAIN
# ==========================

def main():
    """
    Точка входа:
      1) читаем пути модулей из modules_list.txt;
      2) строим список моделей и полей;
      3) запускаем GUI tkinter; при ошибке — печатаем в консоль.
    """
    key = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    mod_paths = read_modules_list(MODULES_LIST_FILE)
    if not mod_paths:
        print("[ОШИБКА] Не найдены пути к модулям. Создайте modules_list.txt и добавьте пути (по одному на строку).")
        sys.exit(1)

    modules = build_modules_info(mod_paths)
    initial = apply_filter(modules, key)

    # Пробуем GUI; если не получилось — печать в консоль
    try:
        show_gui(initial, initial_filter=key)
    except Exception:
        print("[ПРЕДУПРЕЖДЕНИЕ] GUI недоступен или произошла ошибка, печатаю в консоль.")
        traceback.print_exc(limit=1)
        print_tree_console(initial)


if __name__ == "__main__":
    main()
