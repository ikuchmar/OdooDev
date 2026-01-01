import os
import subprocess
from pathlib import Path


# ==============================
# 🔧 НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ
# ==============================

SOURCE_FOLDER = r"D:\Entertaiment\Shweik2"      # Папка с исходными файлами
OUTPUT_FOLDER = r"D:\Entertaiment\Shweik3"     # Куда сохранять результат
SPEED = 1.20                         # Коэффициент ускорения (1.1 = 10% быстрее)

# ==============================


def build_atempo_filter(speed: float) -> str:
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
    src = Path(SOURCE_FOLDER)
    dst = Path(OUTPUT_FOLDER)
    dst.mkdir(parents=True, exist_ok=True)

    if not src.is_dir():
        print(f"❌ Папка не найдена: {src}")
        return

    mp3_files = list(src.glob("*.mp3"))
    if not mp3_files:
        print("❗ В исходной папке нет mp3-файлов.")
        return

    atempo = build_atempo_filter(SPEED)

    print(f"📁 Источник: {src}")
    print(f"💾 Выход:    {dst}")
    print(f"⚡ Скорость:  x{SPEED}\n")

    for file in mp3_files:
        out_file = dst / f"{file.stem}_x{SPEED:.2f}.mp3"

        print(f"▶ {file.name} → {out_file.name}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(file),
            "-filter:a", atempo,
            "-vn",
            str(out_file),
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            print("   ✔ Готово\n")
        else:
            print("   ❌ Ошибка при обработке")
            print(result.stderr, "\n")

    print("🏁 Обработка завершена.")


if __name__ == "__main__":
    process_all()
