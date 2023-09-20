from odoo import fields, models


class AdvancedFields(models.Model):
    _inherit = '_tu_helper.field'

    field_binary = fields.Binary(string='Binary',
                                 attachment=True,
                                 copy=False,
                                 help='This is Binary field')

    # --------------------------------------------------------------------------------------
    # Binary - Поле, що дозволяє зберігати бінарні об’єкти - файли. Може мати пусте значення
    # На формі має вигляд посилання файл або елементу файл у режимі редагування
    # --------------------------------------------------------------------------------------

    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).
    #  attachment -  whether the field should be stored as ir_attachment or in a column of the model’s table (default: True).
    #  должно ли поле храниться как ir_attachment или в столбце таблицы модели (по умолчанию: True).
    #  copy - – whether the field value should be copied when the record is duplicated
    #  (следует ли копировать значение поля при дублировании записи)
    # help - подсказка при наведении пользователем на поле


