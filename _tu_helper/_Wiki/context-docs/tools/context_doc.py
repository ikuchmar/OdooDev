#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Docs Viewer — простой локальный просмотрщик документации из Markdown с расширенным поиском.
Один файл. Только стандартная библиотека. Python 3.8+.

СТРУКТУРА КОДА (упрощена и задокументирована):
1) Докстринг (вы здесь)
2) Импорты
3) Константы
4) Вспомогательные функции парсинга .md
5) Поисковые функции
6) Построение деревьев для UI (категории и файлы)
7) Утилиты (открытие файлов, буфер обмена, относительные пути)
8) Класс App_UI (вся логика интерфейса и взаимодействия с готовыми данными)
9) main()
10) if __name__ == '__main__': main()

ОСНОВНАЯ ЛОГИКА:
- Рекурсивно сканируем папку docs/, которая находится на ОДИН уровень ВЫШЕ скрипта (../docs).
- Игнорируем служебные папки: node_modules, .git, site, .venv, venv, __pycache__.
- Читаем .md файлы в UTF-8, при ошибке — cp1251.
- Парсим секции, начинающиеся с заголовка "## <ключ>".
- После заголовка опционально распознаём "categories: ..." и/или "aliases: ...".
- Из каждой секции извлекаем: display_key, key, tokens, categories, aliases, file_path, start_line, markdown, code_blocks.
- Поиск поддерживает: точное совпадение ключа, совпадение по алиасам, подстроку, совпадение по токенам, fuzzy-поиск.
- Интерфейс tkinter строго по заданной схеме.

ПРИМЕЧАНИЕ ПО ПРОСТОТЕ:
- Код намеренно написан максимально линейно и подробно прокомментирован — без лишних абстракций.
- Все структуры — обычные dict/list, чтобы не перегружать понимание.
"""

# 2) Импорты
import os
import sys
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 3) Константы
IGNORED_DIRS = {"node_modules", ".git", "site", ".venv", "venv", "__pycache__"}

# Настройки шрифтов/иконок для дерева — используем простые эмодзи для наглядности
ICON_FOLDER = "📁 "
ICON_FILE = "📄 "
ICON_SECTION = "§ "

# 4) Вспомогательные функции парсинга .md

def read_text_file(path: Path) -> str:
    """
    Читает текстовый файл. Сначала пытается UTF-8, если не получилось — cp1251.
    Зачем: в разных источниках файлы могут быть сохранены в разных кодировках.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1251", errors="replace")


def normalize_key(s: str) -> str:
    """
    Приводит ключ к нижнему регистру и обрезает пробелы.
    Зачем: хранить единообразное представление ключа для поиска.
    """
    return (s or "").strip().lower()


def tokenize(s: str) -> List[str]:
    """
    Разбивает строку на токены по любым символам, НЕ являющимся a-z, 0-9, или _.
    Пример: 'ul-ol-li' -> ['ul','ol','li']
    Зачем: поддержать поиск по частям ключа и более гибкую фильтрацию.
    """
    s = normalize_key(s)
    # re.split вернёт список строк между разделителями
    tokens = re.split(r"[^a-z0-9_]+", s)
    # Удалим пустые элементы, если между разделителями ничего не было
    return [t for t in tokens if t]


def parse_aliases_line(line: str) -> List[str]:
    """
    Парсит строку алиасов вида: 'aliases: a1, a2; a3 a4'
    Разделители — запятая, точка с запятой, пробелы. Регистр игнорируется.
    Зачем: чтобы пользователь мог перечислять синонимы произвольно.
    """
    # Отрежем префикс 'aliases:' (без регистра), затем разобьём по , ; и пробелам
    body = re.sub(r"(?i)^aliases:\s*", "", line).strip()
    # Разобьём по запятым/точкам с запятой и пробелам
    raw = re.split(r"[,\s;]+", body)
    return [normalize_key(a) for a in raw if a]


def parse_categories_line(line: str) -> List[str]:
    """
    Парсит строку категорий вида: 'categories: Категория 1 - Подкатегория - ...'
    Разделитель — дефис (с пробелами вокруг опционально).
    Глубина не ограничена.
    Зачем: построение дерева категорий в UI.
    """
    body = re.sub(r"(?i)^categories:\s*", "", line).strip()
    # Разбиваем по дефисам с опциональными пробелами вокруг
    raw = re.split(r"\s*-\s*", body)
    # Возвращаем как есть (без normalize), т.к. категории отображаем “красиво”, с исходным регистром
    return [c.strip() for c in raw if c.strip()]


def extract_code_blocks(markdown: str) -> List[Dict[str, str]]:
    """
    Извлекает кодовые блоки из текста секции.
    Поддерживает любые языки: после ``` может быть что угодно (в т.ч. 'c++' или 'tsx').
    Зачем: отдельная панель для удобного копирования кода.
    """
    code_blocks = []
    # Разбираем построчно, т.к. проще корректно отслеживать открытие/закрытие блока
    lines = markdown.splitlines()
    in_block = False
    lang = ""
    buf = []

    for line in lines:
        # Открытие блока кода: строка начинается с ```
        if not in_block and line.strip().startswith("```"):
            in_block = True
            # Язык — всё, что после ``` до конца строки (может быть пустым)
            lang = line.strip()[3:].strip()
            buf = []
            continue
        # Закрытие блока кода
        if in_block and line.strip().startswith("```"):
            code_blocks.append({"lang": lang, "code": "\n".join(buf)})
            in_block = False
            lang = ""
            buf = []
            continue
        # Внутри блока — просто накапливаем строки
        if in_block:
            buf.append(line)

    return code_blocks


def parse_markdown_file(path: Path, docs_root: Path) -> List[Dict]:
    """
    Парсит один .md файл на секции по заголовкам '## <ключ>'.
    Возвращает список словарей-секций.
    Каждая секция содержит:
      - display_key: исходный ключ (без изменений)
      - key: нормализованный ключ (lowercase)
      - tokens: токены ключа (для поиска)
      - categories: список категорий (могут отсутствовать)
      - aliases: список алиасов (lowercase)
      - file_path: абсолютный путь к файлу (Path)
      - rel_path: путь к файлу относительно корня docs (str)
      - start_line: номер строки, где встречен заголовок (int, начиная с 1)
      - markdown: полный markdown-содержимое секции (str)
      - code_blocks: список блоков кода [{'lang':..., 'code':...}, ...]
    """
    text = read_text_file(path)
    lines = text.splitlines()
    sections: List[Dict] = []

    current = None  # текущая секция, пока накапливаем
    current_lines: List[str] = []
    start_line = 0

    # Вспомогательная функция для сохранения накопленной секции
    def flush_section():
        if current is None:
            return
        md = "\n".join(current_lines).strip()
        # Извлечём кодовые блоки
        code_blocks = extract_code_blocks(md)
        # Запишем в результирующий список
        sections.append({
            "display_key": current["display_key"],
            "key": normalize_key(current["display_key"]),
            "tokens": tokenize(current["display_key"]),
            "categories": current.get("categories", []),
            "aliases": current.get("aliases", []),
            "file_path": path,
            "rel_path": str(path.relative_to(docs_root)),
            "start_line": start_line,
            "markdown": md,
            "code_blocks": code_blocks,
        })

    i = 0
    while i < len(lines):
        line = lines[i]
        # Заголовок новой секции — строка начинается с '## ' (две решётки и пробел)
        if line.startswith("## "):
            # Если предыдущая секция была — сохраним её
            flush_section()
            # Начинаем новую секцию
            header_text = line[3:].strip()  # текст после '## '
            current = {
                "display_key": header_text,
                "categories": [],
                "aliases": [],
            }
            current_lines = []  # обнуляем буфер содержимого
            start_line = i + 1  # номер строки (человекочитаемый, с 1)

            # Сразу после заголовка могут идти строки categories:/aliases: в любом порядке,
            # их считаем частью "метаданных", а не контента секции.
            j = i + 1
            while j < len(lines):
                mline = lines[j].strip()
                # Если наткнулись на новый заголовок — метаданные закончились
                if mline.startswith("## "):
                    break
                # Пропустим чистые разделители '===' или '---' — они опциональны и ни на что не влияют
                if set(mline) <= {"=", "-"} and len(mline) >= 3:
                    j += 1
                    continue
                # categories:
                if re.match(r"(?i)^categories:\s*", mline):
                    current["categories"] = parse_categories_line(mline)
                    j += 1
                    continue
                # aliases:
                if re.match(r"(?i)^aliases:\s*", mline):
                    current["aliases"] = parse_aliases_line(mline)
                    j += 1
                    continue
                # Пустую строку после метаданных просто пропустим
                if mline.strip() == "":
                    j += 1
                    continue
                # Иначе — это уже контент секции
                break

            # Теперь с позиции j начинаем накапливать содержимое секции
            i = j
            continue

        # Если секция уже начата — накапливаем контент построчно
        if current is not None:
            current_lines.append(line)

        i += 1

    # В конце файла не забудем сохранить последнюю секцию
    flush_section()
    return sections


def scan_docs(docs_root: Path) -> Tuple[List[Dict], Dict[Path, List[Dict]]]:
    """
    Рекурсивно сканирует каталог docs_root, игнорируя служебные папки.
    Собирает все .md файлы и парсит их секции.
    Возвращает:
      - список всех секций (list)
      - словарь file->list[sections] (для построения дерева файлов)
    """
    all_sections: List[Dict] = []
    file_map: Dict[Path, List[Dict]] = {}

    for dirpath, dirnames, filenames in os.walk(docs_root):
        # Фильтрация игнорируемых директорий — модифицируем dirnames на месте,
        # чтобы os.walk не заходил внутрь
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for name in filenames:
            if not name.lower().endswith(".md"):
                continue
            fpath = Path(dirpath) / name
            sections = parse_markdown_file(fpath, docs_root)
            if sections:
                file_map[fpath] = sections
                all_sections.extend(sections)

    return all_sections, file_map

# 5) Поисковые функции

def build_indexes(sections: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Строит простые индексы для ускорения поиска.
    Возвращает словарь:
      - 'by_key' -> dict[str, List[section]]
      - 'by_alias' -> dict[str, List[section]]
    Зачем: чтобы быстро находить точные совпадения.
    """
    by_key: Dict[str, List[Dict]] = {}
    by_alias: Dict[str, List[Dict]] = {}
    for s in sections:
        by_key.setdefault(s["key"], []).append(s)
        for a in s.get("aliases", []):
            by_alias.setdefault(a, []).append(s)
    return {"by_key": by_key, "by_alias": by_alias}


def fuzzy_ratio(a: str, b: str) -> float:
    """
    Простейший fuzzy-алгоритм на базе сравнения последовательностей.
    Используем стандартную библиотеку (без внешних зависимостей).
    Возвращает значение 0..1, где 1 — максимальная похожесть.
    """
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def score_section(query: str, query_tokens: List[str], s: Dict]) -> Tuple[int, float]:
    """
    Вычисляет "вес" (приоритет) совпадения секции с запросом.
    Возвращает пару (priority, fuzzy), где priority — целое число (больше — важнее),
    а fuzzy — дробное (для доп. сортировки в рамках одного приоритета).

    Приоритеты (чем больше, тем выше в выдаче):
      1000 — точное совпадение ключа
       900 — точное совпадение алиаса
       800 — подстрока в ключе/алиасах
       700 — совпадения по токенам
       400 — fuzzy-похожие ключ/алиасы (>0.6)

    Зачем: упорядочить кандидатов от наиболее релевантных.
    """
    key = s["key"]
    aliases = s.get("aliases", [])
    tokens = s.get("tokens", [])

    # 1) Точное совпадение ключа
    if query == key:
        return 1000, 1.0
    # 2) Точное совпадение алиаса
    if query in aliases:
        return 900, 1.0
    # 3) Подстрока в ключе или алиасах
    if query and (query in key or any(query in a for a in aliases)):
        return 800, 1.0
    # 4) Совпадения по токенам (любое пересечение токенов запроса и ключа)
    if query_tokens and any(t in tokens for t in query_tokens):
        # Чем больше пересечений — тем лучше. Но для простоты ставим один уровень.
        return 700, 1.0
    # 5) Fuzzy — берём максимум похожести по ключу и алиасам
    fuzz_key = fuzzy_ratio(query, key) if query else 0.0
    fuzz_ali = max((fuzzy_ratio(query, a) for a in aliases), default=0.0) if query else 0.0
    fuzz = max(fuzz_key, fuzz_ali)
    if fuzz >= 0.6:
        return 400, fuzz
    return 0, fuzz


def search_sections(query_raw: str, sections: List[Dict], indexes: Dict[str, Dict[str, List[Dict]]]) -> Tuple[Optional[Dict], List[Dict]]:
    """
    Основная функция поиска.
    Возвращает кортеж:
      (best_section_or_None, candidates_sorted_list)
    Где best_section — первый в списке, если есть точное совпадение/наивысший приоритет.
    Если кандидатов несколько — UI предложит выбрать из списка.

    Правила приоритета:
      - если есть точное совпадение ключа — оно первое;
      - затем точные совпадения алиасов;
      - затем подстрочные, токенные, и т.д.
    """
    query = normalize_key(query_raw)
    if not query:
        return None, []

    query_tokens = tokenize(query)

    # Сначала соберём кандидатов — пройдем по всем секциям и посчитаем рейтинг
    scored: List[Tuple[int, float, Dict]] = []
    for s in sections:
        prio, fuzz = score_section(query, query_tokens, s)
        if prio > 0:
            scored.append((prio, fuzz, s))

    # Если ничего не найдено — вернём пустой результат
    if not scored:
        return None, []

    # Сортировка: по приоритету (убыв.), затем по fuzzy (убыв.), затем по ключу (алфавит)
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]["display_key"]))
    candidates = [s for (_, _, s) in scored]

    # Лучший — первый
    best = candidates[0] if candidates else None
    return best, candidates

# 6) Построение деревьев для UI

def build_category_index(sections: List[Dict]) -> Dict[Tuple[str, ...], List[Dict]]:
    """
    Строит индекс категорий: ключ — кортеж из пути категорий ('Web','HTML','Списки'),
    значение — список секций внутри этой "папки".
    Зачем: упростить построение дерева для вкладки "Категории".
    """
    idx: Dict[Tuple[str, ...], List[Dict]] = {}
    for s in sections:
        cats = tuple(s.get("categories", []) or [])
        idx.setdefault(cats, []).append(s)
    return idx


def build_file_tree_map(file_map: Dict[Path, List[Dict]], docs_root: Path) -> Dict:
    """
    Из словаря file->sections строит простую древовидную структуру для дерева файлов.
    Возвращает вложенные dict:
      {"dir": {"subdir": {...}, "file.md": [sections...]}, ...}
    Зачем: чтобы легко отрисовать структуру каталогов и файлов с секциями.
    """
    tree = {}
    for fpath, sections in file_map.items():
        rel = fpath.relative_to(docs_root)
        parts = rel.parts
        node = tree
        for p in parts[:-1]:  # все папки
            node = node.setdefault(p, {})
        # последний элемент — файл
        node.setdefault(parts[-1], sections)
    return tree

# 7) Утилиты

def open_in_system(path: Path) -> None:
    """
    Открывает файл/папку штатной программой ОС.
    Windows: os.startfile
    macOS: 'open'
    Linux: 'xdg-open'
    Зачем: кнопка 'Открыть .md'.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")


def copy_to_clipboard(root: tk.Tk, text: str) -> None:
    """
    Копирует текст в буфер обмена без всплывающих окон.
    Зачем: быстрый доступ к содержимому.
    """
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось скопировать в буфер обмена:\n{e}")


def relpath(path: Path, base: Path) -> str:
    """
    Возвращает путь path относительно base в виде строки.
    Зачем: компактно показывать пути в UI.
    """
    try:
        return str(path.relative_to(base))
    except Exception:
        return str(path)

# 8) Класс App_UI — вся логика интерфейса и работы с уже готовыми данными

class App_UI:
    """
    UI-класс. На вход получает готовые структуры данных: список секций, деревья.
    Внутри — только логика интерфейса: отрисовка, обработчики событий, история.
    """

    def __init__(self, root: tk.Tk, docs_root: Path, sections: List[Dict], file_map: Dict[Path, List[Dict]]):
        self.root = root
        self.docs_root = docs_root
        self.sections = sections
        self.file_map = file_map

        # Индексы и вспомогательные отображения
        self.indexes = build_indexes(sections)
        self.cat_index = build_category_index(sections)
        self.file_tree_map = build_file_tree_map(file_map, docs_root)

        # История открытых секций (по уникальному id)
        self.history: List[Tuple[str, int]] = []  # список (rel_path, start_line)
        self.history_pos: int = -1  # позиция текущего элемента в истории
        self.current_section: Optional[Dict] = None

        # Построим интерфейс
        self._build_ui()

    # ---------- построение интерфейса ----------

    def _build_ui(self) -> None:
        self.root.title("Context Docs Viewer")
        self.root.geometry("1100x700")

        # ВЕРХНЯЯ ПАНЕЛЬ (Topbar) — строго по схеме
        topbar = ttk.Frame(self.root, padding=6)
        topbar.pack(side=tk.TOP, fill=tk.X)

        # Кнопка Назад
        self.btn_back = ttk.Button(topbar, text="◀", width=3, command=self.on_back)
        self.btn_back.pack(side=tk.LEFT)

        # Отступ 4px
        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)

        # Кнопка Вперёд
        self.btn_fwd = ttk.Button(topbar, text="▶", width=3, command=self.on_forward)
        self.btn_fwd.pack(side=tk.LEFT)

        # Отступ 10px
        ttk.Frame(topbar, width=10).pack(side=tk.LEFT)

        # Метка Поиск:
        ttk.Label(topbar, text="Поиск:").pack(side=tk.LEFT)

        # Поле ввода — растягивается на всё оставшееся пространство
        self.entry_search = ttk.Entry(topbar)
        self.entry_search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry_search.bind("<Return>", lambda e: self.on_search())

        # Отступ 4px
        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)

        # Кнопка Искать
        ttk.Button(topbar, text="Искать", command=self.on_search).pack(side=tk.LEFT)

        # Отступ 4px
        ttk.Frame(topbar, width=4).pack(side=tk.LEFT)

        # Кнопка Найти в дереве
        ttk.Button(topbar, text="Найти в дереве", command=self.on_locate_in_trees).pack(side=tk.LEFT)

        # ОСНОВНАЯ ОБЛАСТЬ — горизонтальный PanedWindow 1:3
        self.pw_main = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        self.pw_main.pack(fill=tk.BOTH, expand=True)

        # Левая часть — Notebook (Категории / Файлы)
        left_frame = ttk.Frame(self.pw_main)  # контейнер под Notebook
        self.pw_main.add(left_frame, weight=1)

        self.nb_left = ttk.Notebook(left_frame)
        self.nb_left.pack(fill=tk.BOTH, expand=True)

        # Вкладка Категории
        tab_categories = ttk.Frame(self.nb_left)
        self.nb_left.add(tab_categories, text="Категории")

        self.tree_categories = ttk.Treeview(tab_categories, show="tree")
        self.tree_categories.pack(fill=tk.BOTH, expand=True)
        self.tree_categories.bind("<Double-1>", self.on_tree_categories_double)

        # Вкладка Файлы
        tab_files = ttk.Frame(self.nb_left)
        self.nb_left.add(tab_files, text="Файлы")

        self.tree_files = ttk.Treeview(tab_files, show="tree")
        self.tree_files.pack(fill=tk.BOTH, expand=True)
        self.tree_files.bind("<Double-1>", self.on_tree_files_double)

        # Правая часть — вертикальный PanedWindow 3:2
        right_frame = ttk.Frame(self.pw_main)
        self.pw_main.add(right_frame, weight=3)

        self.pw_right = ttk.Panedwindow(right_frame, orient=tk.VERTICAL)
        self.pw_right.pack(fill=tk.BOTH, expand=True)

        # Верхняя панель (Markdown-текст)
        top_md = ttk.Frame(self.pw_right, padding=6)
        self.pw_right.add(top_md, weight=3)

        self.txt_md = tk.Text(top_md, wrap=tk.NONE, font=("Consolas", 11))
        self.txt_md.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_md = ttk.Scrollbar(top_md, orient=tk.VERTICAL, command=self.txt_md.yview)
        scroll_md.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_md.configure(yscrollcommand=scroll_md.set)

        # Нижняя панель (Кодовые блоки)
        bottom_code = ttk.Frame(self.pw_right, padding=6)
        self.pw_right.add(bottom_code, weight=2)

        # Верхняя строка — выбор блока
        bar_code = ttk.Frame(bottom_code)
        bar_code.pack(fill=tk.X)

        ttk.Label(bar_code, text="Кодовые блоки:").pack(side=tk.LEFT)
        ttk.Frame(bar_code, width=6).pack(side=tk.LEFT)

        self.cb_blocks = ttk.Combobox(bar_code, state="readonly")
        self.cb_blocks.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cb_blocks.bind("<<ComboboxSelected>>", lambda e: self.on_block_selected())

        # Текстовое поле кода
        self.txt_code = tk.Text(bottom_code, wrap=tk.NONE, font=("Consolas", 11), height=12)
        self.txt_code.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(6, 6))

        scroll_code = ttk.Scrollbar(bottom_code, orient=tk.VERTICAL, command=self.txt_code.yview)
        scroll_code.pack(side=tk.RIGHT, fill=tk.Y, pady=(6, 6))
        self.txt_code.configure(yscrollcommand=scroll_code.set)

        # Нижняя строка (кнопки)
        bar_bottom = ttk.Frame(bottom_code)
        bar_bottom.pack(fill=tk.X)

        ttk.Button(bar_bottom, text="Скопировать весь блок", command=self.on_copy_section).pack(side=tk.LEFT)
        ttk.Frame(bar_bottom, width=4).pack(side=tk.LEFT)
        ttk.Button(bar_bottom, text="Скопировать код", command=self.on_copy_code).pack(side=tk.LEFT)
        ttk.Frame(bar_bottom, width=4).pack(side=tk.LEFT)
        ttk.Button(bar_bottom, text="Открыть .md", command=self.on_open_md).pack(side=tk.LEFT)

        # Справа — кнопка Закрыть (используем растягивающийся пустой фрейм как пружину)
        ttk.Frame(bar_bottom).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(bar_bottom, text="Закрыть", command=self.root.destroy).pack(side=tk.RIGHT)

        # Заполнение деревьев
        self._populate_trees()

        # Установим примерные пропорции панелей 1:3 и 3:2
        self.root.update_idletasks()
        try:
            w = self.pw_main.winfo_width()
            self.pw_main.sashpos(0, int(w * 0.25))  # 1:3
            h = self.pw_right.winfo_height()
            self.pw_right.sashpos(0, int(h * 0.6))  # 3:2
        except Exception:
            pass

        # Обновим состояние кнопок истории
        self._update_history_buttons()

    # ---------- заполнение деревьев ----------

    def _populate_trees(self) -> None:
        # Категории: построим иерархию. Ключ — кортеж путей категорий.
        self.tree_categories.delete(*self.tree_categories.get_children())
        self.cat_node_map = {}  # (категория путь tuple) -> item_id
        self.cat_section_item = {}  # (rel_path, start_line) -> item_id

        # Сначала соберём все уникальные пути категорий и добавим их в дерево
        # Пустые категории ([]) тоже допустимы — такие секции поместим в корень
        # Отсортируем для стабильного отображения
        paths = sorted(self.cat_index.keys())
        # Чтобы гарантировать наличие родительских папок, создадим по частям
        for path_tuple in paths:
            parent_id = ""
            built = ()
            for part in path_tuple:
                built = built + (part,)
                if built not in self.cat_node_map:
                    # Вставляем узел категории
                    text = part
                    item_id = self.tree_categories.insert(parent_id, "end", text=text, open=False)
                    self.cat_node_map[built] = item_id
                    parent_id = item_id
                else:
                    parent_id = self.cat_node_map[built]

        # Теперь добавим листовые элементы — секции
        for path_tuple, secs in self.cat_index.items():
            parent_id = self.cat_node_map.get(path_tuple, "")
            for s in sorted(secs, key=lambda x: x["display_key"]):
                uid = (s["rel_path"], s["start_line"])
                text = f"{ICON_SECTION}{s['display_key']} ({s['rel_path']})"
                item_id = self.tree_categories.insert(parent_id, "end", text=text, open=False, values=(uid,))
                self.cat_section_item[uid] = item_id

        # Файлы: дерево каталогов/файлов
        self.tree_files.delete(*self.tree_files.get_children())
        self.file_item_map = {}      # rel_dir path -> item_id (папка)
        self.file_section_item = {}  # (rel_path, start_line) -> item_id
        self._add_file_tree_nodes("", self.file_tree_map)

    def _add_file_tree_nodes(self, parent_id: str, node) -> None:
        # Рекурсивно строим дерево по структуре из build_file_tree_map
        if isinstance(node, dict):
            # Внутренний узел: либо папки, либо файлы
            for name in sorted(node.keys()):
                child = node[name]
                if isinstance(child, dict):
                    # Это папка
                    item_id = self.tree_files.insert(parent_id, "end", text=f"{ICON_FOLDER}{name}", open=False)
                    self._add_file_tree_nodes(item_id, child)
                else:
                    # Это файл — child = [sections...]
                    sections = child
                    item_id = self.tree_files.insert(parent_id, "end", text=f"{ICON_FILE}{name}", open=False)
                    # Добавим дочерние узлы — секции этого файла
                    for s in sorted(sections, key=lambda x: x["display_key"]):
                        uid = (s["rel_path"], s["start_line"])
                        sec_id = self.tree_files.insert(item_id, "end", text=f"{ICON_SECTION}{s['display_key']}", values=(uid,))
                        self.file_section_item[uid] = sec_id
        else:
            # Неожиданный тип узла — игнорируем (по простой логике сюда не попадём)
            pass

    # ---------- обработчики событий ----------

    def on_tree_categories_double(self, event=None):
        # Определим выбранный элемент
        item_id = self.tree_categories.focus()
        if not item_id:
            return
        # Проверим, является ли узел секцией (у него есть values с uid)
        values = self.tree_categories.item(item_id, "values")
        if values:
            uid = eval(values[0]) if isinstance(values[0], str) else values[0]
            self._open_section_by_uid(uid)

    def on_tree_files_double(self, event=None):
        item_id = self.tree_files.focus()
        if not item_id:
            return
        # Если это секция (есть values) — откроем её
        values = self.tree_files.item(item_id, "values")
        if values:
            uid = eval(values[0]) if isinstance(values[0], str) else values[0]
            self._open_section_by_uid(uid)
            return
        # Если это файл — попытаемся открыть первую секцию из его детей
        children = self.tree_files.get_children(item_id)
        for ch in children:
            vals = self.tree_files.item(ch, "values")
            if vals:
                uid = eval(vals[0]) if isinstance(vals[0], str) else vals[0]
                self._open_section_by_uid(uid)
                break

    def on_search(self):
        query = self.entry_search.get().strip()
        if not query:
            return
        best, candidates = search_sections(query, self.sections, self.indexes)
        if not candidates:
            messagebox.showinfo("Поиск", "Ничего не найдено.")
            return
        # Если несколько кандидатов и первый не является единственным "очевидным",
        # предложим выбрать. Но если первое — точное совпадение, всё равно покажем список,
        # где оно будет первым (как требовалось).
        self._show_candidates_dialog(candidates)

    def on_block_selected(self):
        # При выборе значения в Combobox — отобразить соответствующий код
        if not self.current_section:
            return
        idx = self.cb_blocks.current()
        blocks = self.current_section.get("code_blocks", [])
        code = blocks[idx]["code"] if 0 <= idx < len(blocks) else ""
        self._set_text(self.txt_code, code)

    def on_copy_section(self):
        # Копируем весь markdown-текст текущей секции
        if not self.current_section:
            return
        copy_to_clipboard(self.root, self.current_section.get("markdown", ""))

    def on_copy_code(self):
        # Копируем содержимое текущего выбранного блока кода
        if not self.current_section:
            return
        idx = self.cb_blocks.current()
        blocks = self.current_section.get("code_blocks", [])
        code = blocks[idx]["code"] if 0 <= idx < len(blocks) else ""
        if not code:
            return
        copy_to_clipboard(self.root, code)

    def on_open_md(self):
        # Открывает исходный .md файл системной программой
        if not self.current_section:
            return
        open_in_system(self.current_section["file_path"])

    def on_locate_in_trees(self):
        # Позиционирует оба дерева на текущей секции
        if not self.current_section:
            return
        uid = (self.current_section["rel_path"], self.current_section["start_line"])
        # Категории
        item_id = self.cat_section_item.get(uid)
        if item_id:
            # Раскроем всех предков
            self._expand_to_item(self.tree_categories, item_id)
            self.tree_categories.see(item_id)
            self.tree_categories.selection_set(item_id)
            self.tree_categories.focus(item_id)
        # Файлы
        item_id = self.file_section_item.get(uid)
        if item_id:
            self._expand_to_item(self.tree_files, item_id)
            self.tree_files.see(item_id)
            self.tree_files.selection_set(item_id)
            self.tree_files.focus(item_id)

    def on_back(self):
        # Переход по истории назад
        if self.history_pos > 0:
            self.history_pos -= 1
            uid = self.history[self.history_pos]
            self._open_section_by_uid(uid, add_to_history=False)

    def on_forward(self):
        # Переход по истории вперёд
        if self.history_pos + 1 < len(self.history):
            self.history_pos += 1
            uid = self.history[self.history_pos]
            self._open_section_by_uid(uid, add_to_history=False)

    # ---------- вспомогательные методы UI ----------

    def _expand_to_item(self, tree: ttk.Treeview, item_id: str) -> None:
        # Рекурсивно раскрывает всех родителей элемента, чтобы сделать его видимым
        parent = tree.parent(item_id)
        if parent:
            self._expand_to_item(tree, parent)
            tree.item(parent, open=True)

    def _set_text(self, widget: tk.Text, text: str) -> None:
        # Установить текст в Text (как read-only для пользователя)
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state=tk.DISABLED)

    def _open_section_by_uid(self, uid: Tuple[str, int], add_to_history: bool = True) -> None:
        # Находит секцию по uid=(rel_path, start_line) и отображает её
        rel_path, start_line = uid
        for s in self.sections:
            if s["rel_path"] == rel_path and s["start_line"] == start_line:
                self._display_section(s, add_to_history=add_to_history)
                return

    def _display_section(self, s: Dict, add_to_history: bool = True) -> None:
        self.current_section = s
        # Верхняя панель — markdown
        self._set_text(self.txt_md, s.get("markdown", ""))
        # Поле поиска — заполняется текущим ключом
        self.entry_search.delete(0, tk.END)
        self.entry_search.insert(0, s.get("display_key", ""))

        # Нижняя панель — кодовые блоки
        blocks = s.get("code_blocks", [])
        items = []
        for i, b in enumerate(blocks, 1):
            lang = b.get("lang") or "text"
            n_lines = len(b.get("code", "").splitlines())
            items.append(f"[{i}] {lang} — {n_lines} строк")
        if not items:
            items = ["— нет кодовых блоков —"]
        self.cb_blocks["values"] = items
        self.cb_blocks.current(0)
        # Установим код
        code0 = blocks[0]["code"] if blocks else ""
        self._set_text(self.txt_code, code0)

        # История
        uid = (s["rel_path"], s["start_line"])
        if add_to_history:
            # Если мы ушли назад и открываем новую секцию — отсечём "вперёд"-ветку
            if 0 <= self.history_pos < len(self.history) - 1:
                self.history = self.history[: self.history_pos + 1]
            # Добавим, если это не повтор текущего
            if not self.history or self.history[-1] != uid:
                self.history.append(uid)
            self.history_pos = len(self.history) - 1
            self._update_history_buttons()

    def _update_history_buttons(self):
        # Включаем/выключаем кнопки истории
        self.btn_back.config(state=(tk.NORMAL if self.history_pos > 0 else tk.DISABLED))
        self.btn_fwd.config(state=(tk.NORMAL if self.history_pos + 1 < len(self.history) else tk.DISABLED))

    def _show_candidates_dialog(self, candidates: List[Dict]) -> None:
        """
        Простое диалоговое окно для выбора секции из списка кандидатов.
        Двойной клик или кнопка ОК — открыть.
        """
        win = tk.Toplevel(self.root)
        win.title("Найдено несколько вариантов")
        win.geometry("700x400")
        win.transient(self.root)
        win.grab_set()

        # Список
        frame = ttk.Frame(win, padding=6)
        frame.pack(fill=tk.BOTH, expand=True)

        lb = tk.Listbox(frame)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=lb.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=scroll.set)

        # Заполним строками вида: "§ key — Кат1/Кат2 — file.md"
        def fmt(s: Dict) -> str:
            cats = " / ".join(s.get("categories", [])) or "—"
            return f"{ICON_SECTION}{s['display_key']} — {cats} — {s['rel_path']}"

        for s in candidates:
            lb.insert(tk.END, fmt(s))

        # Кнопки
        bar = ttk.Frame(win, padding=(0, 6, 0, 0))
        bar.pack(fill=tk.X)
        ttk.Button(bar, text="ОК", command=lambda: do_open()).pack(side=tk.RIGHT)
        ttk.Button(bar, text="Отмена", command=win.destroy).pack(side=tk.RIGHT)

        def do_open():
            sel = lb.curselection()
            if not sel:
                return
            idx = int(sel[0])
            s = candidates[idx]
            self._display_section(s, add_to_history=True)
            win.destroy()

        def on_dbl(_event=None):
            do_open()

        lb.bind("<Double-1>", on_dbl)

        # Выделим первый элемент по умолчанию
        if candidates:
            lb.selection_set(0)

# 9) main()

def main():
    # Определим корень проекта: скрипт находится в tools/, docs на уровень выше
    script_path = Path(__file__).resolve()
    docs_root = script_path.parent.parent / "docs"

    if not docs_root.exists():
        # Если папка не найдена — можно использовать соседнюю папку 'docs' относительно рабочей директории
        docs_root = Path.cwd() / "docs"

    # Сканируем и парсим документацию
    sections, file_map = scan_docs(docs_root)

    # Запускаем UI
    root = tk.Tk()
    app = App_UI(root, docs_root, sections, file_map)

    # Если передан аргумент командной строки — выполним автопоиск
    # Пример: python context_doc.py <ключ>
    if len(sys.argv) >= 2:
        query = " ".join(sys.argv[1:]).strip()
        if query:
            app.entry_search.delete(0, tk.END)
            app.entry_search.insert(0, query)
            app.on_search()

    root.mainloop()


# 10) Точка входа
if __name__ == "__main__":
    main()
