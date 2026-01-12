import os
import shutil

def flatten_and_copy_files(source_dir, target_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            # Получаем относительный путь от source_dir
            relative_path = os.path.relpath(file_path, source_dir)
            # Разделяем на части и создаём новое имя
            path_parts = os.path.normpath(relative_path).split(os.sep)
            new_filename = "__".join(path_parts)
            target_path = os.path.join(target_dir, new_filename)

            # Копируем файл
            shutil.copy2(file_path, target_path)
            print(f"Скопирован: {file_path} -> {target_path}")

# Пример использования:
source_directory = "D:\Entertaiment\Аудио\kvitka2\Svatannya na Goncharivci"
target_directory = "D:\Entertaiment\Аудио\kvitka2\Svatannya na Goncharivci2"
flatten_and_copy_files(source_directory, target_directory)
