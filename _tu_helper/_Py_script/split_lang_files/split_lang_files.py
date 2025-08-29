#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой утилитарный скрипт: проходит по исходному пути (файл или папка),
и для каждого подходящего файла создаёт в каталоге приёмника три файла:
<имя>_en<расширение>, <имя>_ru<расширение> и (если найден блок "Новые слова")
<имя>_di<расширение>.

Логика распределения строк:
- Если в строке присутствуют кириллические символы (диапазон U+0400..U+04FF),
  строка идёт в "русский" файл (_ru).
- Иначе — в "английский" файл (_en).
- Пустые строки внутри текста записываются в оба файла (сохраняем разрывы).
- Блок "Новые слова" (поддерживаются варианты "Новые слова" и "🆕 Новые слова")
  выделяется в отдельный список и записывается в файл с суффиксом _di.
  Содержимое этого блока НЕ попадает в _en/_ru.

Дополнительно:
- Во всех выходных файлах удаляются ведущие пустые строки (в начале текста).
- Конфиг читается из config.json (по умолчанию из текущей папки).
- Любые ключи конфига, начинающиеся с '_' — игнорируются.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Iterable, Tuple, Optional, List

# ===============================
# Константы и регулярные выражения
# ===============================

# Регулярка для обнаружения хотя бы одного кириллического символа в строке
RE_CYRILLIC = re.compile(r"[\u0400-\u04FF]")

# Заголовок блока "Новые слова" (поддерживаем с эмодзи и без, регистр не важен)
RE_DICT_HEADER = re.compile(
    r"^\s*(?:🆕\s*)?(?:Новые\s+слова|New\s+words)\s*:?\s*$",
    re.IGNORECASE
)

# Имя файла конфигурации по умолчанию
DEFAULT_CONFIG_NAME = "config.json"


# ===============================
# Утилитарные функции
# ===============================

def load_config(config_path: Optional[str]) -> Dict[str, Any]:
    """
    Загружает конфигурацию из JSON-файла.
    Игнорирует любые ключи, начинающиеся с '_' (например, комментарии).
    Возвращает словарь с параметрами и значениями по умолчанию для отсутствующих ключей.
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_NAME

    cfg_file = Path(config_path)
    if not cfg_file.exists():
        raise FileNotFoundError(f"Не найден файл конфигурации: {cfg_file.resolve()}")

    with cfg_file.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    # Удаляем все служебные ключи, начинающиеся с "_"
    cleaned = {k: v for k, v in raw.items() if not str(k).startswith("_")}

    # Значения по умолчанию
    cfg = {
        "source_path": cleaned.get("source_path", "").strip(),
        "dest_root": cleaned.get("dest_root", "").strip(),
        "extensions": cleaned.get("extensions", []),
        "encoding": cleaned.get("encoding", "utf-8"),
        "preserve_structure": bool(cleaned.get("preserve_structure", True)),
        "overwrite": bool(cleaned.get("overwrite", True)),
        "dry_run": bool(cleaned.get("dry_run", False)),
    }

    if not cfg["source_path"]:
        raise ValueError("В конфиге не указан 'source_path'.")
    if not cfg["dest_root"]:
        raise ValueError("В конфиге не указан 'dest_root'.")

    # Нормализуем расширения: к нижнему регистру и добавляем точку при необходимости
    exts = cfg["extensions"]
    if isinstance(exts, list):
        norm_exts = []
        for e in exts:
            if not e:
                continue
            e = str(e).strip().lower()
            if not e:
                continue
            if not e.startswith("."):
                e = "." + e
            norm_exts.append(e)
        cfg["extensions"] = norm_exts
    else:
        # Если extensions не список — игнорируем фильтр
        cfg["extensions"] = []

    return cfg


def is_text_file_selected(path: Path, extensions: Iterable[str]) -> bool:
    """
    Проверяет, подходит ли файл под фильтр расширений.
    Если список extensions пуст — считаем, что подходят все файлы.
    """
    if not path.is_file():
        return False
    if not extensions:
        return True
    return path.suffix.lower() in set(extensions)


def iter_source_files(source_path: Path, extensions: Iterable[str]) -> Iterable[Path]:
    """
    Итератор по исходным файлам для обработки.
    Поддерживает как одиночный файл, так и рекурсивный проход по папке.
    """
    if source_path.is_file():
        if is_text_file_selected(source_path, extensions):
            yield source_path
        return

    if source_path.is_dir():
        for p in source_path.rglob("*"):
            if is_text_file_selected(p, extensions):
                yield p
        return

    raise FileNotFoundError(f"Источник не найден: {source_path}")


def classify_line(line: str) -> str:
    """
    Классифицирует строку по наличию кириллицы.
    Возвращает 'ru' если в строке выявлена кириллица, иначе 'en'.
    Примечание: пустые строки будем писать в оба файла отдельно, снаружи.
    """
    return "ru" if RE_CYRILLIC.search(line) else "en"


def build_output_paths(src_file: Path, cfg: Dict[str, Any], source_root: Optional[Path]) -> Tuple[Path, Path, Path]:
    """
    Формирует пути приёмников для трёх файлов (_en, _ru, _di).

    Если preserve_structure=True и source_root задан:
      - Вычисляем относительный путь src_file относительно source_root
      - Создаём аналогичную структуру в dest_root

    Если source_root не задан (например, источник — одиночный файл), то файлы
    создаются прямо в dest_root.

    Возвращает (path_en, path_ru, path_di).
    """
    dest_root = Path(cfg["dest_root"])
    preserve = cfg["preserve_structure"]

    # Имя файла без расширения и само расширение
    stem = src_file.stem
    suffix = src_file.suffix  # Сохраняем то же расширение

    # Базовая папка назначения
    if preserve and source_root and src_file.is_relative_to(source_root):
        rel = src_file.relative_to(source_root).parent  # относительный каталог
        target_dir = dest_root / rel
    else:
        target_dir = dest_root

    # Полные пути к файлам приёмникам
    out_en = target_dir / f"{stem}_en{suffix}"
    out_ru = target_dir / f"{stem}_ru{suffix}"
    out_di = target_dir / f"{stem}_di{suffix}"
    return out_en, out_ru, out_di


def ensure_parent_dir(path: Path, dry_run: bool) -> None:
    """
    Обеспечивает существование родительской папки для указанного файла.
    """
    parent = path.parent
    if not parent.exists():
        if dry_run:
            print(f"[DRY-RUN] Создал бы папку: {parent}")
        else:
            parent.mkdir(parents=True, exist_ok=True)


def strip_leading_blank_lines(lines: List[str]) -> List[str]:
    """
    Удаляет ведущие пустые строки (в начале текста).
    Пустой строкой считаем ту, у которой line.strip() == ''.
    """
    i = 0
    n = len(lines)
    while i < n and not lines[i].strip():
        i += 1
    return lines[i:]


def split_content_into_buckets(lines: Iterable[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Разносит входные строки по трём корзинам: EN, RU и DI (словарь).
    - Когда встречаем заголовок блока "Новые слова" — все последующие строки
      пишем только в DI (до конца файла).
    - Пустые строки внутри основного текста дублируем в EN и RU.
    - В конце удаляем ведущие пустые строки из каждой корзины.
    """
    en_lines: List[str] = []
    ru_lines: List[str] = []
    di_lines: List[str] = []

    in_dict_block = False

    for line in lines:
        # Если уже попали в блок словаря — всё уходит в DI, без классификации
        if in_dict_block:
            di_lines.append(line)
            continue

        # Проверяем заголовок словаря
        if RE_DICT_HEADER.match(line):
            in_dict_block = True
            di_lines.append(line)
            continue

        # Основной текст: классифицируем строки
        if not line.strip():
            # Пустую строку дублируем в оба файла
            en_lines.append(line)
            ru_lines.append(line)
            continue

        lang = classify_line(line)
        if lang == "ru":
            ru_lines.append(line)
        else:
            en_lines.append(line)

    # Удаляем ведущие пустые строки в каждой из корзин
    en_lines = strip_leading_blank_lines(en_lines)
    ru_lines = strip_leading_blank_lines(ru_lines)
    di_lines = strip_leading_blank_lines(di_lines)

    return en_lines, ru_lines, di_lines


def write_if_needed(path: Path, content_lines: List[str], encoding: str, overwrite: bool, dry_run: bool) -> None:
    """
    Записывает контент в файл, если есть что писать.
    Соблюдает флаги overwrite/dry_run. Создаёт родительские папки.
    """
    if not content_lines:
        # Пустой список — нечего записывать
        return

    if not overwrite and path.exists():
        print(f"[SKIP] Уже существует (overwrite=False): {path}")
        return

    ensure_parent_dir(path, dry_run)

    if dry_run:
        print(f"[DRY-RUN] Создал бы файл: {path} (строк: {len(content_lines)})")
        return

    with path.open("w", encoding=encoding, newline="") as f:
        f.writelines(content_lines)


def split_file_by_language(src_file: Path, out_en: Path, out_ru: Path, out_di: Path, encoding: str,
                           overwrite: bool, dry_run: bool) -> None:
    """
    Разбивает содержимое src_file на три корзины (EN, RU, DI) и пишет в соответствующие файлы.
    DI-файл создаётся только если обнаружен и не пуст после очистки начала.
    """
    print(f"[PROCESS] {src_file} ->")
    print(f"          EN: {out_en}")
    print(f"          RU: {out_ru}")
    print(f"          DI: {out_di} (только при наличии блока 'Новые слова')")

    if dry_run:
        # В режиме dry-run читаем, чтобы показать предполагаемые действия
        with src_file.open("r", encoding=encoding, errors="replace") as fin:
            en_lines, ru_lines, di_lines = split_content_into_buckets(fin.readlines())
        if en_lines:
            print(f"[DRY-RUN]  -> EN: {len(en_lines)} строк(и)")
        if ru_lines:
            print(f"[DRY-RUN]  -> RU: {len(ru_lines)} строк(и)")
        if di_lines:
            print(f"[DRY-RUN]  -> DI: {len(di_lines)} строк(и)")
        return

    # Обычный режим: читаем и пишем корзины
    with src_file.open("r", encoding=encoding, errors="replace") as fin:
        en_lines, ru_lines, di_lines = split_content_into_buckets(fin.readlines())

    # Запись файлов (если есть контент)
    write_if_needed(out_en, en_lines, encoding, overwrite, dry_run=False)
    write_if_needed(out_ru, ru_lines, encoding, overwrite, dry_run=False)
    write_if_needed(out_di, di_lines, encoding, overwrite, dry_run=False)


def main(argv: Optional[Iterable[str]] = None) -> int:
    """
    Точка входа:
    - Читает конфиг (путь можно передать первым аргументом командной строки,
      иначе используется config.json в текущей папке).
    - Собирает список файлов-источников.
    - Для каждого создаёт парные файлы _en/_ru и, при наличии блока словаря, _di.
    """
    argv = list(argv or sys.argv[1:])
    config_path = argv[0] if argv else None

    try:
        cfg = load_config(config_path)
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки конфига: {e}")
        return 1

    source_path = Path(cfg["source_path"]).resolve()
    dest_root = Path(cfg["dest_root"]).resolve()
    extensions = cfg["extensions"]
    encoding = cfg["encoding"]
    preserve_structure = cfg["preserve_structure"]
    overwrite = cfg["overwrite"]
    dry_run = cfg["dry_run"]

    print("[INFO] Конфигурация:")
    print(f"  source_path       : {source_path}")
    print(f"  dest_root         : {dest_root}")
    print(f"  extensions        : {extensions if extensions else '(все файлы)'}")
    print(f"  encoding          : {encoding}")
    print(f"  preserve_structure: {preserve_structure}")
    print(f"  overwrite         : {overwrite}")
    print(f"  dry_run           : {dry_run}")
    print()

    # Определяем корень для относительных путей (нужен для зеркалирования структуры)
    source_root: Optional[Path] = None
    if source_path.is_dir():
        source_root = source_path

    try:
        files = list(iter_source_files(source_path, extensions))
    except Exception as e:
        print(f"[ERROR] Ошибка обхода источника: {e}")
        return 1

    if not files:
        print("[WARN] Не найдено ни одного файла для обработки по заданным условиям.")
        return 0

    # Создаём корневую папку приёмника (если её нет)
    if not dry_run:
        dest_root.mkdir(parents=True, exist_ok=True)
    else:
        print(f"[DRY-RUN] Создал бы (при необходимости) папку приёмника: {dest_root}")

    # Обрабатываем файлы
    total = 0
    for src in files:
        out_en, out_ru, out_di = build_output_paths(src, cfg, source_root)
        try:
            split_file_by_language(src, out_en, out_ru, out_di, encoding, overwrite, dry_run)
            total += 1
        except Exception as e:
            print(f"[ERROR] {src}: {e}")

    print(f"\n[DONE] Обработано файлов: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
