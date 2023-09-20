from collections import deque

dict_list1 = {
    'm5': ['m1'],
    # 'm2': ['m3', 'm5'],
    'm2': ['m3'],
    'm4': ['m3'],
    'm1': ['m2', 'm3'],
    'm3': [],
}

# Создаем словарь для хранения индекса каждого ключа
key_indices = {key: index for index, key in enumerate(dict_list1)}

# Создаем словарь, где каждому ключу сопоставляем множество его зависимостей
dependencies = {key: set(values) for key, values in dict_list1.items()}

# Инициализируем очередь для выполнения топологической сортировки
queue = deque()

# Добавляем в очередь все ключи, у которых нет зависимостей
for key in dict_list1:
    if not any(key in dependencies[other_key] for other_key in dict_list1):
        queue.append(key)

# Выполняем топологическую сортировку
sorted_keys = []
while queue:
    key = queue.popleft()
    sorted_keys.append(key)

    # Обновляем зависимости у оставшихся ключей
    for other_key in dict_list1:
        if key in dependencies[other_key]:
            dependencies[other_key].remove(key)
            if not any(other_key in dependencies[key] for key in dict_list1):
                queue.append(other_key)

# Проверяем, что все ключи были упорядочены
if len(sorted_keys) != len(dict_list1):
    print("Ошибка: словарь содержит циклические зависимости!")
else:
    # Формируем новый словарь с упорядоченными ключами
    sorted_dict = {key: dict_list1[key] for key in sorted_keys}
    print(sorted_dict)
