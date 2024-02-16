=============================================================
__sql_constraints	это проверка на уникальность имени діє на рівні СУБД
=============================================================
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

--------------------------------------
1. это name_uniq это просто название
2. unique(name) это SQL часть запроса
3. Tag name это просто информация клиенту, если условие не выполнилось
----------------------------------------


альтернативу см . @api.constrains
_tu_helper/_Wiki/_Odoo/Docs/Методы/@api.constrains.txt



class Tags(models.Model):

    _name = "cgu_test_filelds.tags"
    _description = "cgu_test_filelds.tags"

     name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

=============================================================
__sql_constraints	- как снять/удалить ранее установленное ограничение
=============================================================
- написать вместо
   _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

   _sql_constraints = [
        ('name_uniq', '', "Tag name already exists !"),
    ]
- так ограничение будет удалено из базы


=============================================================
delete_sql_constraints() - удаления SQL-ограничения (метод объекта cursor)
=============================================================
from odoo import api, SUPERUSER_ID

def _remove_sql_constraint(cr):
    cr.execute('ALTER TABLE table_name DROP CONSTRAINT constraint_name')

def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute("SAVEPOINT pre_drop;")
    try:
        _remove_sql_constraint(env.cr)
        env.cr.execute("COMMIT;")
    except Exception as e:
        env.cr.execute("ROLLBACK TO pre_drop;")
        raise e
Вы можете вызвать этот метод в методе update() в вашем __manifest__.py файле следующим образом:


def update(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    post_init_hook(cr, registry)

