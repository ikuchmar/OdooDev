
from odoo import fields, models


class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_integer = fields.Integer(string='Integer',
                                   default=1,
                                   required=True,
                                   help='This is Integer field')

    # --------------------------------------------------------------------------------------
    # Integer -  Цілочислове поле. Може приймати лише цілі значення. За замовчанням 0. Не може мати значення “Не встановлено”.
    # --------------------------------------------------------------------------------------
    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # ( метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

    # default -  значение поля по умолчанию

    # required -  требуется заполнение значения

    # help - подсказка при наведении пользователем на поле

