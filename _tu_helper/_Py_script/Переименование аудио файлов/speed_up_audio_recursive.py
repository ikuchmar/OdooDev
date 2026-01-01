import subprocess
from pathlib import Path


# ==============================
# 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ==============================

# Папка с исходными файлами (будет обходиться рекурсивно)
SOURCE_FOLDER = r"D:\Entertaiment\Berrouz_Edgar_-_Marsianskie_voyny_1_Doch_tysyachi_dzheddakov_(Zmeev_Ilya)"

# Корневая папка, куда сохранять результат
# (будет воссоздана структура подкаталогов из SOURCE_FOLDER)
OUTPUT_FOLDER = r"D:\Entertaiment\Berrouz_Edgar_-_Marsianskie_voyny_1_Doch_tysyachi_dzheddakov_(Zmeev_Ilya)2"

# Коэффициент ускорения (1.10 = на 10% быстрее)
SPEED = 1.20

# Расширения, которые обрабатываем (в нижнем регистре, без точки)
AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a"}

# ==============================


def build_atempo_filter(speed: float) -> str:
    """Формирует строку фильтра atempo для ffmpeg.
    atempo принимает значения от 0.5 до 2.0,
    поэтому для больших/меньших скоростей фильтры можно "цепочкой" соединить.
    """
    if speed <= 0:
        raise ValueError("Скорость должна быть > 0")

    filters = []
    remaining = speed

    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0

    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5

    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


def process_all():
    src_root = Path(SOURCE_FOLDER)
    dst_root = Path(OUTPUT_FOLDER)

    if not src_root.is_dir():
        print(f"❌ Папка не найдена: {src_root}")
        return

    dst_root.mkdir(parents=True, exist_ok=True)

    atempo = build_atempo_filter(SPEED)

    print(f"📁 Источник: {src_root}")
    print(f"💾 Выход:    {dst_root}")
    print(f"⚡ Скорость:  x{SPEED}\n")

    # Список всех подходящих файлов
    audio_files = [
        p for p in src_root.rglob("*")
        if p.is_file() and p.suffix.lower().lstrip(".") in AUDIO_EXTENSIONS
    ]

    if not audio_files:
        print("❗ В исходной папке (и подкаталогах) нет аудио-файлов с нужными расширениями.")
        return

    print(f"Найдено файлов: {len(audio_files)}\n")

    for src_file in audio_files:
        # Относительный путь от корня источника
        rel_path = src_file.relative_to(src_root)
        rel_dir = rel_path.parent

        # Папка назначения с сохранением структуры
        out_dir = dst_root / rel_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Имя файла: исходное имя + суффикс скорости
        out_name = f"{src_file.stem}_x{SPEED:.2f}{src_file.suffix}"
        dst_file = out_dir / out_name

        print(f"▶ {src_file} \n   → {dst_file}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(src_file),
            "-filter:a", atempo,
            "-vn",
            str(dst_file),
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode == 0:
            print("   ✔ Готово\n")
        else:
            print("   ❌ Ошибка при обработке")
            print(result.stderr, "\n")

    print("🏁 Обработка завершена.")


if __name__ == "__main__":
    process_all()
