from collections import defaultdict


def topological_sort(dependencies):
    # Создаем словарь для хранения посещенных узлов
    visited = defaultdict(bool)

    # Создаем список для сохранения упорядоченных зависимостей
    ordered_result = []

    # Рекурсивная функция для обхода узлов в глубину
    def dfs(node):
        # Помечаем текущий узел как посещенный
        visited[node] = True

        # Рекурсивно обходим зависимости текущего узла
        if node in dependencies:
            for dependency in dependencies[node]:
                # Если зависимость не была посещена, вызываем функцию dfs для нее
                if not visited[dependency]:
                    dfs(dependency)

        # Добавляем текущий узел в начало списка результата
        ordered_result.insert(0, node)

    # Обходим все узлы словаря dependencies
    for node in dependencies:
        # Если узел не был посещен, вызываем функцию dfs для него
        if not visited[node]:
            dfs(node)

    # Создаем новый словарь depends_2 с упорядоченными зависимостями
    depends_2 = {}
    for node in ordered_result:
        depends_2[node] = depends_1.get(node, [])

    return depends_2


# Исходный словарь с зависимостями
depends_1 = {
    'm5': ['m1'],
    'm4': ['m3'],
    'm1': ['m2', 'm3'],
    'm2': ['m3', 'm5'],
    'm3': [],
}

# Получаем упорядоченные зависимости
depends_2 = ordered_dependencies = topological_sort(depends_1)



print(depends_2)
