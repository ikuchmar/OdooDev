uninstall_hook
=========================
это функция, которая выполняется при удалении модуля. Этот хук может использоваться для
выполнения любых необходимых действий при деинсталляции модуля, таких как очистка данных, удаление настроек или отмена
изменений, внесенных модулем.

Пример использования uninstall_hook
Рассмотрим пример, в котором мы создадим модуль с uninstall_hook, который будет удалять определенные записи из базы
данных при деинсталляции модуля.

Структура модуля
markdown

custom_uninstall_hook/
├── __init__.py
├── __manifest__.py
├── models/
│ ├── __init__.py
│ ├── custom_model.py
__manifest__.py


# __manifest__.py  - определите uninstall_hook.

    {
    'name': 'Custom Uninstall Hook',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Module with uninstall hook example',
    'description': """
    This module demonstrates how to use uninstall_hook in Odoo.
    ""',
    'author': 'Your Name',
    'depends': ['base'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
    }

# __init__.py - импортируйте модель и функцию хука.

    from . import models
    from .uninstall import uninstall_hook

# models/__init__.py - Импортируйте модель.
    from . import custom_model

# models/custom_model.py


    from odoo import models, fields
    
    class CustomModel(models.Model):
    _name = 'custom.model'
    _description = 'Custom Model'
    
        name = fields.Char(string='Name')

#  uninstall.py в корневом каталоге модуля и определите функцию uninstall_hook.


    from odoo import api, SUPERUSER_ID
    
    def uninstall_hook(cr, registry):
    with api.Environment.manage():
    env = api.Environment(cr, SUPERUSER_ID, {})
    # Пример удаления всех записей модели 'custom.model' при деинсталляции модуля
    custom_models = env['custom.model'].search([])
    custom_models.unlink()


# Пояснение
uninstall_hook: Определите функцию, которая будет выполнять необходимые действия при деинсталляции модуля. В этом
примере мы удаляем все записи из модели custom.model.
api.Environment.manage(): Управляет контекстом среды, чтобы обеспечить правильное выполнение операций с базой данных.
SUPERUSER_ID: Используется для выполнения операций с правами суперпользователя.
Установка и удаление модуля
Поместите модуль custom_uninstall_hook в каталог addons.
Обновите список модулей через интерфейс Odoo.
Установите модуль через интерфейс Odoo.
Создайте несколько записей в модели custom.model.
Удалите модуль через интерфейс Odoo.
Проверьте, что записи модели custom.model были удалены.
Заключение
Использование uninstall_hook в Odoo позволяет выполнять любые необходимые действия при деинсталляции модуля. Это может
быть полезно для очистки данных, удаления настроек или отмены изменений, внесенных модулем, обеспечивая чистоту и
корректность системы после удаления модуля.