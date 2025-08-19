# -*- coding: utf-8 -*-
"""
Небольшие утилиты: нормализация ключей, токенизация, распознавание разделителей.
"""

import re
from typing import List

# Разделители (строки из === или --- любой длины, с пробелами)
SEP_LINE_RE = re.compile(r"^\s*[=\-]{3,}\s*$")
# Разбиение на токены для поиска
TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9_]+")

def normalize_key(s: str) -> str:
    """Нормализация ключей/запросов: обрезать пробелы, привести к нижнему регистру."""
    return (s or "").strip().lower()

def tokenize(s: str) -> List[str]:
    """
    Разбить строку на токены по небуквенно-цифровым (кроме '_').
    Пример: 'ul-ol-li' -> ['ul','ol','li']
    """
    s = normalize_key(s)
    return [t for t in TOKEN_SPLIT_RE.split(s) if t]

def is_sep_line(s: str) -> bool:
    """Проверить, является ли строка разделителем ===/--- (с учётом пробелов)."""
    return bool(SEP_LINE_RE.match(s or ""))
