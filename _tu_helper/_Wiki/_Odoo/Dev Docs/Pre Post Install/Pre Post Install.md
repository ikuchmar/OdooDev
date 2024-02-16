Если вы хотите обновить данные при установке или обновлении модуля,
вы можете использовать метод post_install() или post_upgrade() соответственно.
 Эти методы вызываются автоматически после установки или обновления модуля.

===============================================
post_install():

from odoo import api, SUPERUSER_ID

def post_install(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    my_model = env['my.model']
    my_records = my_model.search([])
    my_records.write({'field_to_update': 'new_value'})
В этом примере мы получаем среду выполнения Environment и используем ее для доступа к модели my.model. Затем мы получаем все записи модели и обновляем поле field_to_update для каждой записи.

===============================================
атрибутом pre_install в файле __manifest__.py
===============================================
'pre_install_hook': 'module_name.pre_install_hook',
где 'module_name' - название модуля, а 'pre_install_hook' - название метода, который должен быть вызван.

{
    'name': 'Module Name',
    'version': '1.0',
    'summary': 'Module summary',
    'description': 'Module description',
    'author': 'Author Name',
    'depends': ['base'],
    'data': [
        # module data files
    ],
    'pre_install': 'module_name.pre_install_hook',
    'post_install': 'module_name.post_install_hook',
}

