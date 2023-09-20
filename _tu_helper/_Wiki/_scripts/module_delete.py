from odoo import api, models


def delete_module(module_name):
    Module = env['ir.module.module']
    module = Module.search([('name', '=', module_name)], limit=1)

    if module:
        # вызываем метод unlink() на записи модуля
        module.unlink()
        print(f"Модуль {module_name} успешно удален")
    else:
        print(f"Модуль {module_name} не найден")

if __name__ == "__main__":
    module_name = 'field_basic'
    delete_module(module_name)