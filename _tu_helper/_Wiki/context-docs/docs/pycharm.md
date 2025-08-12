==========================
## live-templates
==========================
PyCharm - Productivity - Шаблоны (Live Templates)
--------------------------------------------
Шаблоны позволяют разворачивать аббревиатуры в код. Пример докстринга для Python.

```text
Abbreviation: doc
Template text:
"""
${DESCRIPTION}
:param ${PARAM}: 
:return: 
"""
Applicable: Python
```
## run-configuration
PyCharm - Запуск - Конфигурации
Создание конфигурации запуска скрипта с аргументами.

```text
Run → Edit Configurations → + Python
Script path: /path/to/app.py
Parameters: --env=dev --debug
Working dir: $ProjectFileDir$
```
