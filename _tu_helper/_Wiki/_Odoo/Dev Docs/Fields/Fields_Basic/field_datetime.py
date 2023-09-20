from odoo import fields, models
from datetime import date


class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_datetime = fields.Datetime(string='Datetime',
                                     store=True,
                                     index=True,
                                     copy=False,
                                     default=date.today(),
                                     help='This is Datetime field')

    # --------------------------------------------------------------------------------------
    # Datetime - Зберігає дані про дату і час. Може мати пусте значення.
    # На формі має вигляд поле з вспливаючим календарем, що має режим редагування часу
    # --------------------------------------------------------------------------------------
    # Datetime fields can only be compared to datetime objects.
    # Поля даты и времени можно сравнивать только с объектами даты и времени.
    # Common operations with dates and datetimes such as addition, subtraction or fetching the start/end of a period are exposed through both Date and Datetime. These helpers are also available by importing odoo.tools.date_utils.
    # (Общие операции с датами и датами, такие как сложение, вычитание или выборка начала/конца периода, доступны как через Date, так и через Datetime. Эти помощники также доступны при импорте odoo.tools.date_utils.)
    # The  Datetime fields class have helper methods to attempt conversion into a compatible type:
    # Класс полей Datetime имеет вспомогательные методы для попытки преобразования в совместимый тип:
    #   to_datetime() будет сконвертирован в  datetime.datetime
    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).
    # required -  требуется заполнение значения
    # help - подсказка при наведении пользователем на поле

