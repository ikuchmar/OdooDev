import re


def clean_srt_file(input_file, output_file):
    """
    Очищает SRT-файл от временных меток и индексов, оставляя только текст.

    :param input_file: Путь к исходному SRT-файлу.
    :param output_file: Путь для сохранения очищенного файла.
    """
    # Шаблон для поиска временных меток
    # timing_pattern = re.compile(r'^\d+\s\d{2}:\d{2}:\d{2},\d{3}\s-->\s\d{2}:\d{2}:\d{2},\d{3}$')
    timing_pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')

    with open(input_file, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    # Убираем строки с временными метками и индексами
    cleaned_lines = []
    for line in lines:
        if timing_pattern.match(line.strip()) or line.strip().isdigit():
            continue
        cleaned_line = line
        cleaned_line = cleaned_line.replace("<i>", "")
        cleaned_line = cleaned_line.replace("</i>", "")
        cleaned_lines.append(cleaned_line)

    # cleaned_lines = [
    #     line for line in lines if not (timing_pattern.match(line.strip()) or line.strip().isdigit())
    # ]

    # Записываем результат в новый файл
    with open(output_file, 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)


# Пример использования
input_file_path = "D:/Entertaimant/1111.srt"  # Замените на ваш файл
output_file_path = "D:/Entertaimant/cleaned_example.txt"
clean_srt_file(input_file_path, output_file_path)