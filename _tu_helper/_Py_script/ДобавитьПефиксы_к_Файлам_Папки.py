import os

def add_prefix_to_files(folder_path, prefix):
    # Получаем список всех файлов в папке
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            new_name = prefix + filename
            new_path = os.path.join(folder_path, new_name)
            os.rename(file_path, new_path)
            print(f"Переименован: {filename} → {new_name}")

# Пример использования
folder = r'D:\Entertaiment\Три мушкетера часть2'  # замените на нужный путь
prefix = 'Mush32_'              # замените на нужный префикс

add_prefix_to_files(folder, prefix)