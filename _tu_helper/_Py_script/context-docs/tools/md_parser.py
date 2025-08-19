# -*- coding: utf-8 -*-
"""
Парсер Markdown и сбор секций из корневых папок.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple

import re
from models import Section
from utils import is_sep_line, normalize_key

# Папки, которые не сканируем
IGNORE_DIRS = {"site", "node_modules", ".git", ".venv", "venv", "__pycache__"}

# Регэкспы для парсинга
HEADER_RE         = re.compile(r"^\s*#{1,6}\s+(.+?)\s*$")     # заголовок: #..###### + текст
ALIASES_RE        = re.compile(r"^\s*aliases\s*:\s*(.+)\s*$", re.I)
CATEGORIES_RE     = re.compile(r"^\s*categories\s*:\s*(.+)\s*$", re.I)
FENCE_START_RE    = re.compile(r"^\s*```([^\s`]+)?\s*$")
FENCE_END_RE      = re.compile(r"^\s*```\s*$")

def parse_md_file(md_path: Path) -> List[Section]:
    """
    Разбирает один .md на список Section.
    Формат (терпимый):
      # или ## ... <ключ>
      (любой порядок строк: aliases: ..., categories: ... (может быть много раз), пустые/разделители)
      <markdown до следующего заголовка>
    """
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    n = len(lines)
    sections: List[Section] = []

    headers = [i for i, line in enumerate(lines) if HEADER_RE.match(line)]
    if not headers:
        return sections
    headers.append(n)  # виртуальный конец

    for idx in range(len(headers) - 1):
        start = headers[idx]
        end   = headers[idx + 1]

        m = HEADER_RE.match(lines[start])
        if not m:
            continue

        display_key = m.group(1).strip()
        key = normalize_key(display_key)

        i = start + 1

        # пропускаем пустые и разделители
        while i < end and (not lines[i].strip() or is_sep_line(lines[i])):
            i += 1

        # читаем мета-строки (любой порядок): aliases:/categories:
        aliases: List[str] = []
        categories_list: List[List[str]] = []

        while i < end:
            s = (lines[i] or "").strip()
            if not s or is_sep_line(s):
                i += 1
                continue

            ma = ALIASES_RE.match(s)
            if ma:
                raw = ma.group(1)
                for a in re.split(r"[,\s;]+", raw):
                    a = normalize_key(a)
                    if a:
                        aliases.append(a)
                i += 1
                continue

            mc = CATEGORIES_RE.match(s)
            if mc:
                cat_line = mc.group(1).strip()
                if " - " in cat_line:
                    levels = [p.strip() for p in cat_line.split(" - ") if p.strip()]
                else:
                    levels = [cat_line] if cat_line else []
                if levels:
                    categories_list.append(levels)
                i += 1
                continue

            break  # начался контент

        # контент секции
        content_lines = lines[i:end]

        # извлечём кодовые блоки (без ограждений)
        codes: List[str] = []
        in_code = False
        cur: List[str] = []
        for line in content_lines:
            if not in_code and FENCE_START_RE.match(line):
                in_code = True
                cur = []
                continue
            if in_code and FENCE_END_RE.match(line):
                codes.append("\n".join(cur))
                in_code = False
                cur = []
                continue
            if in_code:
                cur.append(line)
        if in_code and cur:
            codes.append("\n".join(cur))

        markdown = "\n".join(content_lines).strip()

        sections.append(Section(
            key=key,
            display_key=display_key,
            aliases=aliases,
            categories_list=categories_list,
            markdown=markdown,
            codes=codes,
            file_path=md_path,
            start_line=start + 1
        ))

    return sections

def collect_sections_from_roots(roots: List[Path]) -> Tuple[List[Path], List[Section]]:
    """
    Идёт по всем корневым папкам, собирает *.md (кроме IGNORE_DIRS), парсит секции.
    Возвращает (список файлов, список секций).
    """
    files: List[Path] = []
    sections: List[Section] = []
    for root in roots:
        for p in sorted(root.rglob("*.md")):
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            files.append(p)
            sections.extend(parse_md_file(p))
    return files, sections
