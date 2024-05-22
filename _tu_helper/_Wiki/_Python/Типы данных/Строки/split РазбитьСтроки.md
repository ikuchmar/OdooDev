# Разбиваем текст на отдельные строки
    lines = text.split('unexpected indent')

# Разбиваем текст по строкам
    conditions_list = self.conditions.split('\n')  


# Используем цикл for для итерации по каждой строке
    for line in lines:
        # Проверяем, начинается ли строка с символа "#"
        if not line.startswith('#'):
            # Если строка НЕ начинается с символа "#", то выводим ее на экран
            print(line)


