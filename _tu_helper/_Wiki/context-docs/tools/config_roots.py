# -*- coding: utf-8 -*-
"""
Чтение верхнеуровневых путей документации из doc_roots.txt.
Если валидных путей нет — используем ../docs.
"""

from pathlib import Path
from typing import List

# Файл со списком путей (рядом с этим модулем)
DOC_ROOTS_FILE = Path(__file__).resolve().parent / "doc_roots.txt"
# Запасной путь по умолчанию
DEFAULT_FALLBACK_DOCS = (Path(__file__).resolve().parent.parent / "docs")

def read_doc_roots() -> List[Path]:
    """Возвращает список существующих папок-корней документации."""
    roots: List[Path] = []
    if DOC_ROOTS_FILE.exists():
        base = DOC_ROOTS_FILE.parent
        for raw in DOC_ROOTS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            if not p.is_absolute():
                p = (base / p).resolve()
            if p.exists() and p.is_dir():
                roots.append(p)

    if not roots:
        fb = DEFAULT_FALLBACK_DOCS.resolve()
        if fb.exists() and fb.is_dir():
            roots.append(fb)

    return roots
