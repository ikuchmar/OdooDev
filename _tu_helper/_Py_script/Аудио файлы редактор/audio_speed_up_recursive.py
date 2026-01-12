"""
Скрипт рекурсивно обходит заданную папку, находит аудио-файлы и меняет их скорость
с помощью ffmpeg (через аудио-фильтр atempo), сохраняя структуру подкаталогов в
выходной директории. Поддерживается dry-run, проверка существующих файлов и
копирование без перекодирования при скорости 1.0.

Как работает в общих чертах:
- ищет аудио по расширениям из AUDIO_EXTENSIONS;
- строит фильтр atempo: при выходе за пределы 0.5–2.0 собирает цепочку фильтров;
- для каждого файла создаёт выходной путь с суффиксом скорости и вызывает ffmpeg;
- умеет пропускать существующие файлы, вести лог и работать в режиме dry-run.
"""

import subprocess
import shutil
import argparse
import sys
import logging
from pathlib import Path


# ==============================
# 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ (по умолчанию)
# ==============================

# Папка с исходными файлами (будет обходиться рекурсивно)
SOURCE_FOLDER = r"D:\Entertaiment\Berrouz_Edgar_-_Marsianskie_voyny_2"

# Корневая папка, куда сохранять результат
# (будет воссоздана структура подкаталогов из SOURCE_FOLDER)
OUTPUT_FOLDER = r"D:\Entertaiment\Berrouz_Edgar_-_Marsianskie_voyny_2_2"

# Коэффициент ускорения (1.10 = на 10% быстрее)
SPEED = 1.20

# Расширения, которые обрабатываем (в нижнем регистре, без точки)
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}


# ==============================
# Назначение: построить строку фильтра atempo для заданной скорости
# ==============================

def build_atempo_filter(speed: float) -> str:
    """Вернуть корректную цепочку фильтров `atempo` под нужный коэффициент скорости.

    Правила ffmpeg: один фильтр atempo принимает значения только в диапазоне 0.5–2.0.
    Если коэффициент выходит за пределы, строим несколько atempo так, чтобы
    произведение множителей дало итоговую скорость. Для скорости, близкой к 1.0,
    возвращается atempo=1.0 без изменений.
    """
    if speed <= 0:
        raise ValueError("Скорость должна быть > 0")

    if abs(speed - 1.0) < 1e-12:
        return "atempo=1.0"

    filters = []
    remaining = float(speed)

    # Разбиваем ускорение на множители не больше 2.0
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0

    # Разбиваем замедление на множители не меньше 0.5
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5  # деление на 0.5 эквивалентно умножению на 2

    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


# ==============================
# Назначение: найти аудио-файлы в каталоге и подкаталогах
# ==============================

def find_audio_files(src_root: Path):
    """Вернуть список файлов с нужными расширениями, найденных через rglob."""
    return [
        p for p in src_root.rglob("*")
        if p.is_file() and p.suffix.lower().lstrip(".") in AUDIO_EXTENSIONS
    ]


# ==============================
# Назначение: выполнить ffmpeg для изменения скорости аудио
# ==============================

def run_ffmpeg(src: Path, dst: Path, atempo_filter: str, dry_run: bool = False) -> tuple:
    """Запустить ffmpeg для перекодирования аудио c нужной скоростью.

    Возвращает:
    - (True, stderr) при успешном выполнении;
    - (False, stderr) при ошибке возврата ffmpeg или исключении;
    - (None, None) если включён dry-run и команда только логируется.
    """
    cmd = [
        "ffmpeg",
        "-y",              # перезапись без вопросов
        "-i", str(src),    # входной файл
        "-filter:a", atempo_filter,  # аудио-фильтр скорости
        "-vn",             # не трогаем возможные видео-дорожки
        str(dst),
    ]

    logging.debug("FFMPEG CMD: %s", " ".join(cmd))

    if dry_run:
        return (None, None)

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as exc:
        return (False, f"ffmpeg not found: {exc}")
    except Exception as exc:
        return (False, str(exc))

    return (result.returncode == 0, result.stderr)


# ==============================
# Назначение: orchestrator — обходит файлы и применяет изменение скорости
# ==============================

def process_all(
    source: str,
    output: str,
    speed: float,
    overwrite: bool = False,
    dry_run: bool = False,
):
    """Найти все подходящие аудио-файлы и применить к ним изменение скорости.

    Делает проверку исходной папки, готовит выходную структуру, строит фильтр
    скорости, затем по каждому файлу формирует путь назначения и вызывает ffmpeg
    (или копирует файл, если скорость ~1.0).
    """
    src_root = Path(source)
    dst_root = Path(output)

    if not src_root.is_dir():
        logging.error("Папка не найдена: %s", src_root)
        return

    dst_root.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        logging.warning("ffmpeg не найден в PATH. Скрипт не сможет обрабатывать аудио, если не установлен ffmpeg.")
        if not dry_run:
            logging.error("Установите ffmpeg или запустите в режиме dry-run.")
            return

    atempo = build_atempo_filter(speed)

    logging.info("Источнику: %s", src_root)
    logging.info("Выход:    %s", dst_root)
    logging.info("Скорость: x%s", speed)
    logging.info("Фильтр:   %s", atempo)

    audio_files = find_audio_files(src_root)

    if not audio_files:
        logging.info("В исходной папке (и подкаталогах) нет аудио-файлов с нужными расширениями.")
        return

    logging.info("Найдено файлов: %d", len(audio_files))

    for src_file in audio_files:
        rel_path = src_file.relative_to(src_root)
        rel_dir = rel_path.parent

        out_dir = dst_root / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        out_name = f"{src_file.stem}_x{speed:.2f}{src_file.suffix}"
        dst_file = out_dir / out_name

        logging.info("Обработка: %s -> %s", src_file, dst_file)

        if dst_file.exists() and not overwrite:
            logging.info("Файл %s уже существует — пропускаем (use --overwrite для перезаписи).", dst_file)
            continue

        if abs(speed - 1.0) < 1e-12:
            if dry_run:
                logging.info("(dry-run) Скопировать: %s -> %s", src_file, dst_file)
            else:
                shutil.copy2(src_file, dst_file)
                logging.info("Скопирован: %s", dst_file)
            continue

        success, stderr = run_ffmpeg(src_file, dst_file, atempo, dry_run=dry_run)

        if success is None:
            logging.info("(dry-run) Команда для %s: ffmpeg ... %s", src_file, atempo)
        elif success:
            logging.info("Готово: %s", dst_file)
        else:
            logging.error("Ошибка при обработке %s:\n%s", src_file, stderr)

    logging.info("Обработка завершена.")


# ==============================
# Назначение: точка входа при запуске скрипта из командной строки
# ==============================

def main(argv=None):
    """Разбор аргументов и запуск основного процесса обработки."""
    parser = argparse.ArgumentParser(description="Ускорить все аудио-файлы рекурсивно (ffmpeg).")
    parser.add_argument("--source", "-s", default=SOURCE_FOLDER, help="Папка-источник")
    parser.add_argument("--output", "-o", default=OUTPUT_FOLDER, help="Папка-выход")
    parser.add_argument("--speed", "-k", type=float, default=SPEED, help="Коэффициент скорости (например 1.2)")
    parser.add_argument("--overwrite", action="store_true", help="Перезаписывать существующие файлы в выходной папке")
    parser.add_argument("--dry-run", action="store_true", help="Не выполнять ffmpeg, только показать, что будет сделано")
    parser.add_argument("--debug", action="store_true", help="Включить debug логирование")

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        process_all(args.source, args.output, args.speed, overwrite=args.overwrite, dry_run=args.dry_run)
    except Exception as exc:
        logging.exception("Неожиданная ошибка: %s", exc)
        sys.exit(1)


# ==============================
if __name__ == "__main__":
    main()
