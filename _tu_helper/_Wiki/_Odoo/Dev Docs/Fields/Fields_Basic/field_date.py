from odoo import fields, models


class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_date = fields.Date(string='Date',
                             index=True,
                             required=True,
                             help='This is Date field')

    # --------------------------------------------------------------------------------------
    # Date - Зберігає дату. Може мати пусте значення.
    # На формі має вигляд поле з вспливаючим календарем
    # --------------------------------------------------------------------------------------

    # Date fields can only be compared to date objects.
    # Поля даты можно сравнивать только с объектами даты.
    # Common operations with dates and datetimes such as addition, subtraction or fetching the start/end of a period are exposed through both Date and Datetime. These helpers are also available by importing odoo.tools.date_utils.
    # (Общие операции с датами и датами, такие как сложение, вычитание или выборка начала/конца периода, доступны как через Date, так и через Datetime. Эти помощники также доступны при импорте odoo.tools.date_utils.)
    # The Date  fields class have helper methods to attempt conversion into a compatible type:
    # Класс полей Date имеет вспомогательные методы для попытки преобразования в совместимый тип:
    #     to_date() будет сконвертирован в datetime.date
    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).
    # required -  требуется заполнение значения
    # --------------------------------------------------------------------------------------
    # Обчислювальні параметри
    # Деякі параметри можуть бути обчислені динамічно. Наприклад, default, domain тощо. Часто при визначені таких параметрів допускають помилку:
    #
    # a_field = fields.Date(default=fields.Date.today())
    #
    # Важливо: в параметр default буде передано результат виконання функції, а не саму функцію, наприклад
    #
    # a_field = fields.Date(default=fields.Date.today)
    #
    # Але для параметрів, які обчислюються, слід використовувати лямбда функцію:
    #
    # a_field = fields.Char(default=lambda self: self._default_a_field_get())
    #
    # Це дозволить успадковувати, розширювати або перевизначати функцію.
    #

    # help - подсказка при наведении пользователем на поле

