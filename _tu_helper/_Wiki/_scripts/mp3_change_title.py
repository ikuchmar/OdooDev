import os
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

# Укажите путь к папке с MP3-файлами
directory = r"D:\Entertaimant\Дюма_А_Граф_Монте_Кристо_Кирсанов_С_3"  # Замените на свою папку

# Обрабатываем все файлы в папке
for filename in os.listdir(directory):
    if filename.lower().endswith(".mp3"):
        file_path = os.path.join(directory, filename)

        try:
            # Загружаем MP3 файл
            audio = MP3(file_path, ID3=EasyID3)

            # Получаем имя файла без расширения
            title = os.path.splitext(filename)[0]

            # Обновляем тег "title"
            audio["title"] = title
            audio.save()

            print(f"✅ Название обновлено: {filename} → {title}")

        except Exception as e:
            print(f"❌ Ошибка с файлом {filename}: {e}")

print("🎵 Готово! Все MP3-файлы обновлены.")