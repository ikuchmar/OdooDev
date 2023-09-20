depends_1 = {
    'm5': ['m1'],
    'm2': ['m3',  'm5'],
    'm4': ['m3'],
    'm1': ['m2', 'm3'],
    'm3': [],
}

# Создаем список всех уникальных ключей из исходного словаря
all_keys = list(set(depends_1.keys()).union(*depends_1.values()))

# Инициализируем словарь depends_2 с пустыми списками значений
depends_2 = {key: [] for key in all_keys}

# Проходим по каждому ключу в исходном словаре
for key in depends_1:
    # Получаем список зависимостей для текущего ключа
    dependencies = depends_1[key]
    # Добавляем текущий ключ в список зависимостей каждого из его зависимостей
    for dependency in dependencies:
        depends_2[dependency].append(key)

print(depends_2)