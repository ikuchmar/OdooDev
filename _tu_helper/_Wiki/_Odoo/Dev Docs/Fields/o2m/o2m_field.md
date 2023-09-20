
from odoo import fields, models


class One2manyFields(models.Model):
    _name = 'field.one2many'

    field_one2many_id = fields.One2many(string='One2many field',
                                        comodel_name='field.many2one',
                                        inverse_name='field_many2one_id',
                                        auto_join=True)

For a one2many field, a lits of tuples is expected. Here is the list of tuple that are accepted, with the corresponding semantics ::

                

(0, 0, { values }) link to a new record that needs to be created with the given values dictionary 
(1, ID, { values }) update the linked record with id = ID (write *values* on it) 
(2, ID) remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well)


    # --------------------------------------------------------------------------------------
    #   Оновлення полів Many2many та One2many
    #   в поле передається список команд, які являють собою кортежі, в яких прописані дії та параметри оновлення
    #   Важливо! x2many можна оновлювати лише в такий спосіб.
    #   В кортежі перший параметр визначає команда, значення двох інших залежать від команди.
    #   Важливо! Кортежі команд можна комбінувати у списку, вони будуть виконуватись одни за одною.
    #   'value_ids': [(5, 0, 0), (0, 0, {'name': 'Service on demand',}), ]
    #   Всього є сім команд
    #   CREATE = 0
    #   UPDATE = 1
    #   DELETE = 2
    #   UNLINK = 3
    #   LINK = 4
    #   CLEAR = 5
    #   SET = 6

    #   create
    #   Кортеж виглядає (0, 0, values)
    #   Другий параметр ігнорується, третій являє собою словник значень, як при створенні запису.
    #   'operation_ids': [
    #    (0, 0, {'name': 'Cutting Machine',  'time_cycle': оператор выполняет объединение двух множеств и присваивает результат обратно в левый операнд,
    #              'workcenter_id': self.workcenter_1.id,  'sequence': 1}),
    #    (0, 0, {'name': 'Weld Machine',  'time_cycle': 18,
    #              'workcenter_id': self.workcenter_1.id,  'sequence': 2}), ]
    #
    #   update
    #   Кортеж виглядає (1, id, values)
    #   В другому параметры передається id запису що пов’язаний, третій словник значень, що будуть оновлені. Якщо перший команда створює нові записи, ця оновлює.
    #
    #   'attribute_line_ids': [(1, template.attribute_line_ids[0].id, {
    #    'attribute_id': pa_color.id,
    #    'value_ids': [(4, pav_color_black.id, False)], })]

    #   delete
    #   Кортеж виглядає (2, id, 0)
    #   В другому параметрі передається id запису, що видаляється, третій ігнорується.
    #   Важливо, запис саме видаляється, якщо у зв’язку Many2many на нього є посилання може виникнути помилка у разі ondelete='restrict'.
    #
    #   company.write({
    #       'country_id': country2.id,
    #       'child_ids': [(2, child_company.id)], })
    #
    #   unlink
    #   Кортеж виглядає (3, id, 0)
    #   В другому параметрі передається id запису, що від’єднується, третій ігнорується.
    #
    #   {'users': [(3, user.id) for user in group_user.users]}
    #
    #   Видаляє запис з таблиці зв'язку. Для One2many, де зворотнє поле має ondelete='cascade' запис буде видалений.
    #
    #   link
    #   Кортеж виглядає (4, id, 0)
    #   В другому параметрі передається id запису, що приєднується, третій ігнорується.
    #   Створює запис в таблиці зв’язку.
    #
    #   {'groups_id': [(4, group.id, False) for group in all_groups]}
    #
    #   clear
    #   Кортеж виглядає (5, 0, 0)
    #   Другий і третій параметри ігноруються.
    #   Видаляє усі зв’язки. Працює так, якби застосувати unlink до усіх пов’язаних записів.
    #
    #   self.warehouse_ids = [(5, 0, 0)]
    #
    #   set
    #   Кортеж виглядає (6, 0, ids)
    #   Другий параметр ігнорується, третій це список (це важливо, саме список) id записів.
    #   Замінює поточний список зв’язків на переданий. Так якби очистити зв’язок і створити нові.
    #
    #   Важливо! Навіть якщо треба передати один id, все одно треба передавати список (список з одного елементу).
    #
    #   values['sale_line_ids'] = [(6, None, self.sale_line_ids.ids)]


    # --------------------------------------------------------------------------------------
    #    string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    #    (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

    #    comodel_name – name of the target model Mandatory except for related or extended fields.
    #    (имя целевой модели Обязательно, за исключением связанных или расширенных полей.)

    #    inverse_name – name of the inverse Many2one field in comodel_name
    #    (— имя обратного поля Many2one в comodel_name)

    #    domain – an optional domain to set on candidate values on the client side (domain or string)
    #    (необязательный домен для установки возможных значений на стороне клиента (домен или строка))

    #    context - an optional context to use on the client side when handling that field
    #    (необязательный контекст для использования на стороне клиента при обработке этого поля)

    #    auto_join - whether JOINs are generated upon search through that field (default: False)
    #    генерируются ли JOIN при поиске по этому полю (по умолчанию: False)

    #   limit - optional limit to use upon read
    #   необязательный лимит для использования при чтении

    #   groups
    #   Строковий. Перелік зовнішніх ID груп, яким дозволений доступ до поля
    #
    #   slide_partner_ids = fields.One2many('slide.slide.partner', 'slide_id', string='Subscribers information', groups='website_slides.group_website_slides_officer', copy=False)
    #
    #   Важливо: До поля не буде доступу також і в інтерфейсі користувача, тому, якщо є залежності від цього поля - у користувача без доступу виникне помилка.
    #







