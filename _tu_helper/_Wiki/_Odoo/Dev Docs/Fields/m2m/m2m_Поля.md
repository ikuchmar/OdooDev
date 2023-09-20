# Конструкция поля типа many2many в Odoo имеет следующий синтаксис:

class MyClass(models.Model):
    _name = 'my.class'

    many2many_field = fields.Many2many(comodel_name='other.class',
                                       relation='my_relation_table',
                                       column1='my_class_id',
                                       column2='other_class_id',
                                       string='Many2many Field',
                                       help='Description of the Many2many field')

----------------------------------------------------------
# comodel_name - имя модели, с которой связано поле типа many2many.

----------------------------------------------------------
# relation
- название таблицы связи между текущей моделью и моделью comodel_name.
  если не задан параметр "явное-название-промежуточной-таблицы",
  то ее название оду генерит автоматически по правилу:
  "название-текущей-модели" + "_" + "название-связанной-модули" + "_rel"

# column1 - название столбца, который связывает текущую модель с таблицей связи.
# column2 - название столбца, который связывает модель comodel_name с таблицей связи.
# string - название поля, которое будет отображаться на форме в интерфейсе пользователя.
# help - описание поля, которое будет отображаться на форме в интерфейсе пользователя в виде всплывающей подсказки.


For a many2many field, a list of tuples is expected. Here is the list of tuple that are accepted, with the corresponding semantics ::

(0, 0, { values }) link to a new record that needs to be created with the given values dictionary 
(1, ID, { values }) update the linked record with id = ID (write *values* on it) 
(2, ID) remove and delete the linked record with id = ID (calls unlink on ID, that will delete the object completely, and the link to it as well) 
(3, ID) cut the link to the linked record with id = ID (delete the relationship between the two objects but does not delete the target object itself) 
(4, ID) link to existing record with id = ID (adds a relationship) 
(5) unlink all (like using (3,ID) for all linked records) 
(6, 0, [IDs]) replace the list of linked IDs (like using (5) then (4,ID) for each ID in the list of IDs)
Example: [(6, 0, [8, 5, 6, 4])] sets the many2many to ids [8, 5, 6, 4]

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

