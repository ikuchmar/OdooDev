# -*- coding: utf-8 -*-
"""
Модели данных.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class Section:
    """
    Одна секция документации.
    - key:          нормализованный ключ (lower)
    - display_key:  как написано в заголовке (для отображения)
    - aliases:      список алиасов (lower)
    - categories_list: список путей категорий (каждый путь — список уровней)
    - markdown:     полный markdown-текст секции (без служебных строк)
    - codes:        список кодовых блоков из ```...``` (без ограждений)
    - file_path:    путь к исходному .md
    - start_line:   строка заголовка в файле (для отладки)
    """
    key: str
    display_key: str
    aliases: List[str]
    categories_list: List[List[str]]
    markdown: str
    codes: List[str]
    file_path: Path
    start_line: int
