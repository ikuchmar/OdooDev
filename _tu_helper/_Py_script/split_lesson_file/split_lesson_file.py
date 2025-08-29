# -*- coding: utf-8 -*-
"""
Скрипт режет текст(ы) по секциям вида:
    2.1 Title
    English:
    ...
    Русский:
    ...
до следующего заголовка формата N.N Title.

Работает в двух режимах (определяется по config.ini):
1) INPUT.source_path = путь к ФАЙЛУ — обработает один файл.
2) INPUT.source_path = путь к ПАПКЕ — рекурсивно найдёт все файлы с расширениями (INPUT.extensions),
   и для каждого создаст набор целевых файлов в OUTPUT, сохраняя симметричную структуру папок.

Имена выходных файлов: "002_01 Title.txt" и т.д. Настройки паддингов и разделителя — в [NAMING].

Файл конфигурации: config.ini (должен лежать рядом со скриптом).
Пример конфигурации см. в переписке или составьте по аналогии:
[INPUT]
source_path = "D:\Work\source\Урок 2\Вход\Урок 2 общий.txt"
extensions = .txt

[OUTPUT]
output_dir = "D:\Work\source\Урок 2\out"
clean_output = no

[NAMING]
pad_chapter_to_3 = yes
pad_section_to_2 = yes
title_separator = " "
extension = .txt

[ADVANCED]
ignore_hidden = yes
skip_files_without_sections = yes
source_encoding = utf-8
output_encoding = utf-8
"""

import os
import re
import shutil
import configparser
from typing import List, Dict

# -------------------------------
# Регулярное выражение заголовка секции
# -------------------------------
SECTION_HEADER_RE = re.compile(r'^\s*(\d+)\.(\d+)\s+(.+?)\s*$', re.UNICODE)

# Недопустимые символы для имени файла в Windows
INVALID_FILENAME_CHARS = r'\/:*?"<>|'


# -------------------------------
# Вспомогательные функции
# -------------------------------
def normalize_path(p: str) -> str:
    """
    Убирает обрамляющие кавычки и пробелы, нормализует слэши.
    Позволяет спокойно писать пути в INI как в кавычках, так и без.
    """
    if p is None:
        return p
    p = p.strip()
    # снять обрамляющие одинарные/двойные кавычки
    if (p.startswith('"') and p.endswith('"')) or (p.startswith("'") and p.endswith("'")):
        p = p[1:-1].strip()
    # нормализуем путь под ОС
    return os.path.normpath(p)


def sanitize_filename(name: str) -> str:
    """
    Делает имя файла безопасным: заменяет запрещённые символы на пробел, сжимает пробелы.
    """
    trans = {ord(ch): ' ' for ch in INVALID_FILENAME_CHARS}
    cleaned = name.translate(trans)
    cleaned = re.sub(r'\s+', ' ', cleaned, flags=re.UNICODE).strip()
    return cleaned


def pad_number(n: int, width: int) -> str:
    """Возвращает число n как строку с ведущими нулями до width символов."""
    return str(n).zfill(width)


def parse_config(cfg_path: str = "config.ini") -> dict:
    """
    Читает config.ini и возвращает словарь настроек с дефолтами.
    Все пути автоматически нормализуются (кавычки удаляются).
    """
    cfg = configparser.ConfigParser()
    if not cfg.read(cfg_path, encoding="utf-8"):
        raise FileNotFoundError(f"Не найден {cfg_path}. Убедитесь, что файл существует и в UTF-8.")

    # INPUT
    source_path = normalize_path(cfg.get("INPUT", "source_path", fallback="source.txt"))
    extensions = cfg.get("INPUT", "extensions", fallback=".txt")
    ext_list = [e.strip().lower() for e in extensions.split(",") if e.strip()]
    if not ext_list:
        ext_list = [".txt"]

    # OUTPUT
    output_dir = normalize_path(cfg.get("OUTPUT", "output_dir", fallback="out"))
    clean_output = cfg.get("OUTPUT", "clean_output", fallback="no").strip().lower() in ("yes", "true", "1")

    # NAMING
    pad_chapter_to_3 = cfg.get("NAMING", "pad_chapter_to_3", fallback="yes").strip().lower() in ("yes", "true", "1")
    pad_section_to_2 = cfg.get("NAMING", "pad_section_to_2", fallback="yes").strip().lower() in ("yes", "true", "1")
    title_separator = cfg.get("NAMING", "title_separator", fallback=" ")
    extension = cfg.get("NAMING", "extension", fallback=".txt")
    if not extension.startswith("."):
        extension = "." + extension

    # ADVANCED
    ignore_hidden = cfg.get("ADVANCED", "ignore_hidden", fallback="yes").strip().lower() in ("yes", "true", "1")
    skip_empty = cfg.get("ADVANCED", "skip_files_without_sections", fallback="yes").strip().lower() in ("yes", "true", "1")
    source_encoding = cfg.get("ADVANCED", "source_encoding", fallback="utf-8").strip()
    output_encoding = cfg.get("ADVANCED", "output_encoding", fallback="utf-8").strip()

    return {
        "source_path": source_path,
        "extensions": ext_list,
        "output_dir": output_dir,
        "clean_output": clean_output,
        "pad_chapter_to_3": pad_chapter_to_3,
        "pad_section_to_2": pad_section_to_2,
        "title_separator": title_separator.strip('"').strip("'"),
        "extension": extension,
        "ignore_hidden": ignore_hidden,
        "skip_empty": skip_empty,
        "source_encoding": source_encoding,
        "output_encoding": output_encoding,
    }


def is_hidden_path(path: str) -> bool:
    """
    Простейшая проверка "скрытости": имя начинается с точки.
    (Атрибуты Windows не проверяем, чтобы не усложнять.)
    """
    name = os.path.basename(path)
    return name.startswith(".")


def read_text_file(path: str, encoding: str) -> str:
    """Читает текстовый файл в указанной кодировке."""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def split_into_sections(text: str) -> List[Dict]:
    """
    Разбивает текст на секции по заголовкам "N.N Title".
    Возвращает список словарей: [{"chapter": int, "section": int, "title": str, "body": str}, ...].
    В body включаем заголовок и текст до следующего заголовка.
    """
    lines = text.splitlines()
    sections = []
    current = None
    buf = []

    for line in lines:
        m = SECTION_HEADER_RE.match(line)
        if m:
            # сохраняем предыдущую секцию
            if current is not None:
                current["body"] = "\n".join(buf).rstrip() + "\n"
                sections.append(current)
                buf = []
            # начинаем новую
            current = {
                "chapter": int(m.group(1)),
                "section": int(m.group(2)),
                "title": m.group(3),
                "body": ""
            }
            buf.append(line)  # заголовок должен остаться в тексте секции
        else:
            if current is not None:
                buf.append(line)
            else:
                # строки до первого заголовка — игнорируем
                continue

    if current is not None:
        current["body"] = "\n".join(buf).rstrip() + "\n"
        sections.append(current)

    return sections


def ensure_dir(path: str):
    """Создаёт папку, если её нет."""
    os.makedirs(path, exist_ok=True)


def build_out_filename(ch: int, sec: int, title: str,
                       pad_ch3: bool, pad_sec2: bool,
                       sep: str, ext: str) -> str:
    """Собирает имя файла '002_01 Title.txt'."""
    ch_str = pad_number(ch, 3) if pad_ch3 else str(ch)
    sec_str = pad_number(sec, 2) if pad_sec2 else str(sec)
    safe_title = sanitize_filename(title)
    return f"{ch_str}_{sec_str}{sep}{safe_title}{ext}"


def write_sections(sections: List[Dict], out_dir: str, naming: dict, out_encoding: str) -> List[str]:
    """
    Записывает секции в out_dir согласно правилам именования.
    Возвращает список путей созданных файлов.
    """
    ensure_dir(out_dir)
    created = []
    for s in sections:
        fname = build_out_filename(
            ch=s["chapter"], sec=s["section"], title=s["title"],
            pad_ch3=naming["pad_chapter_to_3"],
            pad_sec2=naming["pad_section_to_2"],
            sep=naming["title_separator"],
            ext=naming["extension"],
        )
        full_path = os.path.join(out_dir, fname)
        with open(full_path, "w", encoding=out_encoding, newline="\n") as f:
            f.write(s["body"])
        created.append(full_path)
    return created


def iter_source_files(root: str, ext_list: List[str], ignore_hidden: bool) -> List[str]:
    """
    Возвращает список путей ко всем файлам с нужными расширениями внутри root (рекурсивно).
    """
    matches = []
    for dirpath, dirnames, filenames in os.walk(root):
        if ignore_hidden:
            # отфильтровать скрытые папки (начинающиеся с точки)
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if ignore_hidden and fn.startswith("."):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in ext_list:
                matches.append(os.path.join(dirpath, fn))
    return matches


def clear_output_dir(path: str):
    """
    Полностью очищает содержимое папки вывода (но саму папку не удаляет).
    Безопасно: удаляем только внутри указанной папки.
    """
    if not os.path.isdir(path):
        return
    for name in os.listdir(path):
        full = os.path.join(path, name)
        if os.path.isdir(full):
            shutil.rmtree(full, ignore_errors=True)
        else:
            try:
                os.remove(full)
            except OSError:
                pass


def process_single_file(src_file: str, output_root: str, relative_dir: str, cfg: dict) -> List[str]:
    """
    Обрабатывает один файл: режет на секции и пишет в output_root/relative_dir.
    Возвращает список созданных файлов.
    """
    text = read_text_file(src_file, cfg["source_encoding"])
    sections = split_into_sections(text)
    if not sections and cfg["skip_empty"]:
        return []
    out_dir = os.path.join(output_root, relative_dir)
    naming = {
        "pad_chapter_to_3": cfg["pad_chapter_to_3"],
        "pad_section_to_2": cfg["pad_section_to_2"],
        "title_separator": cfg["title_separator"],
        "extension": cfg["extension"],
    }
    return write_sections(sections, out_dir, naming, cfg["output_encoding"])


# -------------------------------
# Точка входа
# -------------------------------
def main():
    cfg = parse_config("config.ini")

    source_path = cfg["source_path"]
    output_root = cfg["output_dir"]

    # Отладочная печать, чтобы сразу видеть, что распарсилось правильно
    print("SOURCE PATH:", source_path)
    print("OUTPUT DIR :", output_root)

    # Подготовка папки вывода
    ensure_dir(output_root)
    if cfg["clean_output"]:
        clear_output_dir(output_root)

    created_total: List[str] = []

    if os.path.isfile(source_path):
        # Режим одного файла
        rel_dir = ""  # корень вывода
        created_total += process_single_file(source_path, output_root, rel_dir, cfg)

    elif os.path.isdir(source_path):
        # Режим папки: рекурсивный обход
        src_root = os.path.abspath(source_path)
        files = iter_source_files(src_root, cfg["extensions"], cfg["ignore_hidden"])
        for fpath in files:
            # Строим относительный путь папки (без имени файла) для зеркальной структуры
            rel_path = os.path.relpath(os.path.dirname(os.path.abspath(fpath)), src_root)
            if rel_path == ".":
                rel_path = ""
            created_total += process_single_file(fpath, output_root, rel_path, cfg)
    else:
        print(f"Ошибка: source_path не найден: {source_path}")
        return

    # Отчёт
    if created_total:
        print("Готово. Созданы файлы:")
        for p in created_total:
            print(" -", p)
    else:
        print("Готово. Ничего не создано (возможно, ни в одном файле не найдено секций).")


if __name__ == "__main__":
    main()
