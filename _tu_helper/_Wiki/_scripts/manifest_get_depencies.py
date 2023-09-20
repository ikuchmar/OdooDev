import os
import ast


def get_module_dependencies(manifest_path):
    """
    Функция для получения зависимостей модуля из файла манифеста.
    """
    with open(manifest_path, 'r') as manifest_file:
        # Читаем содержимое файла
        manifest_content = manifest_file.read()
        # Разбираем содержимое файла в структуру данных Python
        manifest_data = ast.literal_eval(manifest_content)

    # Проверяем, что блок 'depends' существует
    if 'depends' not in manifest_data:
        print("В файле __manifest__.py не найден блок 'depends'")
        return False

    list_depends_item = []
    # Проходим по всем файлам в списке
    for depends_item in manifest_data['depends']:
        list_depends_item.append(depends_item)

    return list_depends_item


def get_module_dependencies_from_folder(folder_path):
    """
    Функция для прохода по модулям в указанной папке и получения зависимостей модулей.
    """
    dict_module_dependencies = {}
    for root, dirs, files in os.walk(folder_path):
        for file_name in files:
            if file_name == '__manifest__.py':
                module_path = os.path.join(root, file_name)
                module_name = os.path.basename(os.path.dirname(module_path))
                list_depends_item = get_module_dependencies(module_path)

                dict_module_dependencies[module_name] = list_depends_item

    return dict_module_dependencies


def get_recursive_module_dependencies(module_name, module_dependencies):
    """
    Рекурсивная функция для получения зависимостей модуля.
    """
    dependencies = []
    if module_name in module_dependencies:
        dependencies = module_dependencies[module_name]
        for dependency in dependencies:
            dependencies += get_recursive_module_dependencies(dependency, module_dependencies)
    return dependencies


def get_installation_order(module_dependencies):
    """
    Функция для определения последовательности установки модулей.
    """
    installation_order = []
    for module_name in module_dependencies:
        dependencies = get_recursive_module_dependencies(module_name, module_dependencies)
        if module_name not in installation_order and all(dep in installation_order for dep in dependencies):
            installation_order.append(module_name)
    return installation_order

def get_module_install_order2(module_dependencies):
    module_graph = {}
    visited = set()

    def dfs(module):
        visited.add(module)
        dependencies = module_graph.get(module, [])
        for dependency in dependencies:
            if dependency not in visited:
                dfs(dependency)

    # for module in modules:
    for module, dependencies in module_dependencies.items():
        #     manifest = odoo.modules.registry.Registry.get(manifest.name)
        # dependencies = manifest.get('depends', [])
        module_graph[module] = dependencies

    for module, dependencies in module_dependencies.items():
        if module not in visited:
            dfs(module)

    return list(visited)

def main():
    folder_path = r"D:\Turbo\turbo.ua"
    module_dependencies = get_module_dependencies_from_folder(folder_path)

    print("Список зависимостей модулей:")
    ind = 0
    for module, dependencies in module_dependencies.items():
        ind += 1
        print(f"{module}: {dependencies}")
        # print(f"{ind} {module}: {dependencies}")

    # module_dependencies = {
    #     'module1': ['module2', 'module3'],
    #     'module2': ['module3'],
    #     'module3': [],
    #     'module4': ['module5'],
    #     'module5': [],
    #     'module6': ['module4'],
    # }

    # installation_order = get_installation_order(module_dependencies)
    # print("Последовательность установки модулей:")
    # for module in installation_order:
    #     print(module)
    install_order = get_module_install_order2(module_dependencies)
    print(install_order)

if __name__ == '__main__':
    main()
