import os

def change_extension_to_md(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".txt"):
                old_path = os.path.join(root, file)
                new_path = os.path.splitext(old_path)[0] + ".md"
                os.rename(old_path, new_path)
                print(f"Файл {file} переименован в {os.path.basename(new_path)}")

# Путь к корневой папке
folder_path = "D:\Odoo\OdooDev\_tu_helper"

# Вызываем функцию для изменения расширения файлов в указанной папке и ее подпапках
change_extension_to_md(folder_path)