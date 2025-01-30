import os
import shutil

# 🔹 Укажите путь к папке с подпапками
source_directory = r"D:\Entertaimant\Дюма_А_Граф_Монте_Кристо_Кирсанов_С"  # Замените на свою папку

# 🔹 Укажите путь к папке, куда надо собрать файлы
destination_directory = r"D:\Entertaimant\Дюма_А_Граф_Монте_Кристо_Кирсанов_С_2"  # Замените на свою папку

# Создаём целевую папку, если её нет
os.makedirs(destination_directory, exist_ok=True)

# Проход по всем файлам и подпапкам
for root, _, files in os.walk(source_directory):
    for file in files:
        source_path = os.path.join(root, file)  # Полный путь к файлу
        destination_path = os.path.join(destination_directory, file)  # Куда перемещаем

        # Если файл с таким же именем уже есть, добавляем суффикс
        counter = 1
        while os.path.exists(destination_path):
            file_name, file_ext = os.path.splitext(file)
            destination_path = os.path.join(destination_directory, f"{file_name}_{counter}{file_ext}")
            counter += 1

        # Перемещение файла
        shutil.move(source_path, destination_path)
        print(f"Перемещён: {source_path} ➝ {destination_path}")

print("✅ Все файлы успешно перемещены!")