from odoo import fields, models


class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_boolean = fields.Boolean(string='Boolean',
                                   default=True,
                                   help='This is boolean field')

    # --------------------------------------------------------------------------------------
    # Boolean
    # --------------------------------------------------------------------------------------
    # Булевське поле. Може мати значення True або False. Не має значення “Не встановлено”. По замовчуванню має значення False.

    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # ( метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

    # default -  значение поля по умолчанию

    # help - подсказка при наведении пользователем на поле