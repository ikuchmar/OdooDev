# -*- coding: utf-8 -*-
"""
Помощник для работы с деревом категорий (Treeview).
"""

from tkinter import ttk
from models import Section

def add_section_to_tree(tree: ttk.Treeview, root_id: str, cat_path, section: Section, instance_number: int) -> None:
    """
    Вставляет секцию в дерево по пути категорий.
    Для уникальности узла секции используем iid вида:
      "sec::<key>::<abs_path>::<instance_number>"
    """
    parent = root_id
    # создаём/находим узлы уровней категорий
    for level in cat_path:
        found = None
        for child in tree.get_children(parent):
            if tree.item(child, "text") == level:
                found = child
                break
        if found is None:
            found = tree.insert(parent, "end", text=level, open=False)
        parent = found

    unique_iid = f"sec::{section.key}::{section.file_path.resolve()}::{instance_number}"
    tree.insert(parent, "end", iid=unique_iid, text=f"§ {section.key}")
