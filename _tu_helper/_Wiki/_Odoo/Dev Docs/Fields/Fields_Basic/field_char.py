

from odoo import fields, models



class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_char = fields.Char(string='Char 1',
                             copy=True,
                             required=False,
                             size=50,
                             trim=False,
                             translate=False,
                             default="Заполни меня",
                             index=False,
                             store=True,
                             readonly=False,
                             # inverse='_inverse_street_name',
                             # search="_search_complete_name",
                             help='This is char field')

    # def _inverse_street_name(self):
    #     for company in self:
    #         company.partner_id.street_name = company.street_name
    #
    # def _search_complete_name(self, operator, values):
    #     if operator in NEGATIVE_TERM_OPERATOIN:
    #         domain = [
    #             "&",
    #             ("name", operator, value)
    #             ("code", operator, value),
    #         ]
    #     else:
    #         domain=[
    #             "|",
    #             ("name", operator, value),
    #             ("name", operator, value),
    #         ]
    #     return domain



    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # ( метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).
    # Якщо її не задати, то система використає назву поля з великої літери, замінить підкреслення на пробіли, прибере суфікси _id та _ids, тощо. Наприклад:
    #
    # user_name => User name
    # sale_order_id => Sale order

    # copy - – whether the field value should be copied when the record is duplicated
    # (следует ли копировать значение поля при дублировании записи)
    # Логічний. Визначає чи буде значення поля скопійовано при дублюванні запису.

    # required -  требуется заполнение значения
    # Логічний. За замовчанням False. Визначає, що поле є обов’язковим і пусте значення не допускається.
    # Діє також при створенні запису через код.

    # size – the maximum size of values stored for that field
    # (максимальное количество сохраняемых в данном поле символов)
    # довжина поля у символах

    # trim - states whether the value is trimmed or not (by default, True).
    # Note that the trim operation is applied only by the web client.
    # (будет ли функция trim применена к значению)

    # translate– enable the translation of the field’s values
    # (доступность перевода значения поля)
    # Логічний. Визначає, чи буде дане поле перекладатися.

    # default -  значение поля по умолчанию
    # Значення або функція. Значення, передане у цей параметр, або результат виконання переданої функції будуть використовуватись як значення за замовчуванням.
    # Це значення використовується не лише для відображення в інтерфейсі користувача, але також при створенні запису через код або імпорт

    # index  – whether the field is indexed in database. Note: no effect on non-stored and virtual fields. (default: False)

    # store - – whether the field is stored in database (default:True, False for computed fields)
    # (хранится ли поле в базе данных (по умолчанию: True, False для вычисляемых полей))

    # readonly -  поле только для чтения
    # Логічний.  За замовчанням False. Якщо встановити в True - поле не можна буде редагувати в інтерфейсі.
    # Важливо: даний параметр впливає виключно на поведінку поля в інтерфейсі, всі маніпуляції з ним через код будуть працювати.

    # invisible - Логічний. За замовчанням False. Якщо встановити в True - поле буде ховатись в інтерфейсі. Використовується як значення за замовчуванням при визначенні поля у відображеннях
    # inverse - Рядок або функція. Визначає алгоритм, за яким буде оброблене введене користувачем значення для обчислювального поля

    # isearch
    # Рядок або функція. Визначає алгоритм, за яким буде проводитись пошук, для полів, що не були збережені в БД.

    # help - подсказка при наведении пользователем на поле
    # Строковий. Підказка користувачу, може мати довгий пояснювальний текст. Використовується тільки для відображення в інтерфейсі.

    # field_char = fields.Char(compute='_compute_get_phone_number')
