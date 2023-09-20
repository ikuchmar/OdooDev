from odoo import fields, models


class AdvancedFields(models.Model):
    _inherit = '_tu_helper.field'

    field_text = fields.Text(string='Text', required=True, help='This is Text field')

    # --------------------------------------------------------------------------------------
    # Text - Або довгий текст. Строкове необмежене поле. Має специфіку при організації повнотекстового пошуку.
    # --------------------------------------------------------------------------------------

    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).
    # required -  требуется заполнение значения
    # help - подсказка при наведении пользователем на поле


