def check_differences_value(dict_list_1, dict_list_2):
    # Создаем список ключей, объединяя ключи обоих словарей
    set_keys = set(list(dict_list_1.keys()) + list(dict_list_2.keys()))

    # Создаем пустой словарь для различающихся значений
    different_values = {}

    # Проходим по каждому ключу
    for key in set_keys:
        # Получаем значения из обоих словарей
        dict_value_1 = dict_list_1.get(key, [])
        dict_value_2 = dict_list_2.get(key, [])

        # Сравниваем значения
        if dict_value_1 != dict_value_2:
            different_values[key] = (dict_value_1, dict_value_2)

    # Возвращаем различающиеся значения
    return different_values


# Пример вызова процедуры
dict_list_1 = {
    'm5': ['m1'],
    'm2': ['m3', 'm5'],
    'm4': ['m3'],
    'm1': ['m2', 'm3'],
    'm3': [],
}

dict_list_2 = {
    'm3': [],
    'm4': ['m3'],
    'm2': ['m3'],
    'm1': ['m2', 'm3'],
    'm5': ['m1'],
}

dict_list_differences = check_differences_value(dict_list_1, dict_list_2)

# Выводим различающиеся значения
print(dict_list_differences)
for key, values in dict_list_differences.items():
    print(f"Key: {key}, Values_1: {values[0]}, Values_2: {values[1]}")

