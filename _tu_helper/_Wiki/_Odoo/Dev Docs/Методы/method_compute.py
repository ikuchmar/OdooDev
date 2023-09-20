from odoo import fields, models, api


# Метод вычисления поля:
class ComputedFields(models.Model):
    _inherit = '_tu_helper.field.basic'

    field_float2 = fields.Float(string='Float 2',
                                digits=(10, 3),
                                required=True,
                                default=0,
                                store=True,
                                help='This is float field')

    field_float3 = fields.Float(string='Float 3',
                                digits=(10, 3),
                                required=True,
                                default=0,
                                store=True,
                                help='This is float field',
                                compute="_compute_float3",
                                compute_sudo=True)



    # =================================================================
    @api.depends('field_float', 'field_float2')
    def _compute_float3(self):
        for record in self:
            record.field_float3 = record.field_float + record.field_float2

    #
    # compute_sudo
    # Логічний. Визначає, чи розрахунки будуть використовуватись права суперкористувача (обмеження прав доступу будуть проігноровані)

# создаем метод _compute_float3 в модели MyModel.
# Этот метод вычисляет значение поля field_float3 на основе значений полей field_float и field_float2.
# декоратор @api.depends для указания, какие поля зависят от вычисляемого поля.
# Когда значение одного из этих полей изменяется, метод будет вызываться для пересчета значения поля field_float3.

# --------------------------------------------------------------------------------------
# compute
# --------------------------------------------------------------------------------------
# sОбчислювальні поля
# Це такі поля, дані в яких розраховуються функцією, а не вводяться користувачем. Задаються за допомогою спеціальних параметрів.
# Поля будь-якого типу можуть бути обчислювальними і за замовчуванням не можуть приймати дані від користувача та не зберігаються в БД.
#
# compute
# Рядок або функція. Передається назва методу, що обчислює значення поля.
# Може бути сам метод, але він має бути визначений перед полем, що не зручно і порушує вимоги щодо оформлення файлів
# Важливо: в результаті виконання функції полю має бути присвоєне коректне значення.
# Може бути сам метод, але він має бути визначений перед полем, що не зручно і порушує вимоги щодо оформлення файлів

# Метод использует декоратор @api.depends для указания, какие поля зависят от вычисляемого поля.
# Когда значение одного из этих полей изменяется, метод будет вызываться для пересчета значения поля my_field.
#
# dependencies can be dotted paths when using sub-fields:
# (Зависимости могут быть  путями с через точку  при использовании подполей:)
# @api.depends('line_ids.value')
# def _compute_total(self):
#   for record in self:
#       record.total = sum(line.value for line in record.line_Ids)
#

# ======== store

# Computed fields are not stored by default, they are computed and returned when requested.
# Setting store=True will store them in the database and automatically enable searching.
# Вычисляемые поля не сохраняются по умолчанию, они вычисляются и возвращаются по запросу.
# Установка store=True сохранит их в базе данных и автоматически включит поиск.
#

# ======== search
# searching on a computed field can also be enabled by setting the search parameter.
# The value is a method name returning a Search domains.
# (поиск в вычисляемом поле также можно включить, установив параметр поиска.
# Значение представляет собой имя метода, возвращающее домены поиска.)
# upper_name = field.Char(compute='compute_upper', search='_search_upper')
#
# def _search_upper(self, operator, value):
#     if operator == 'like':
#        operator = 'ilike'
#     return [('name', operator, value)]

# The search method is invoked when processing domains before doing an actual search on the model.
# It must return a domain equivalent to the condition: field operator value.
# (Метод поиска вызывается при обработке доменов перед выполнением фактического поиска в модели.
# Он должен возвращать домен, эквивалентный условию: значение оператора поля.)
#

# ====== inverse
# Computed fields are readonly by default.
# To allow setting values on a computed field, use the inverse parameter.
# It is the name of a function reversing the computation and setting the relevant fields:
# (По умолчанию вычисляемые поля доступны только для чтения.)
# (Чтобы разрешить установку значений в вычисляемом поле, используйте параметр inverse.)
# (Это имя функции, обращающей вычисления и устанавливающей соответствующие поля:)
#  document = fields.Char(compute='_get_document', inverse='_set_document')
#  def _get_document(self):
#       for record in self:
#           with open(record.get_document_path) as f:
#               record.document = f.read()
#  def _set_document(self):
#       for record in self:
#           if not record.document: comtinue
#           with open(record.get_document_path()) as f:
#               f.write(record.document)
#
# ====== несколько полей - вычислены одновременно одним и тем же методом
#   multiple fields can be computed at the same time by the same method, just use the same method on all fields and set all of them:
#   (несколько полей могут быть вычислены одновременно одним и тем же методом, просто используйте один и тот же метод для всех полей и установите их все:)
#   discount_value = fields.Float(compute='_apply_discount')
#   total = fields.Float(compute='_apply_discount')
#
#   @api.depends('value', 'discount')
#   def _apply_discount(self):
#       for record in self:
#           # compute actual discount from discount parcentage
#           discount = record.value * record.discount
#           record.discount_value = discount
#           record.total = record.value - discount
#
#  Warning
#   While it is possible to use the same compute method for multiple fields,
#   it is not recommended to do the same for the inverse method.
#   During the computation of the inverse, all fields that use said inverse are protected, meaning that they can’t be computed, even if their value is not in the cache.
#
#   If any of those fields is accessed and its value is not in cache, the ORM will simply return a default value of False for these fields.
#   This means that the value of the inverse fields (other than the one triggering the inverse method) may not give their correct value
#   and this will probably break the expected behavior of the inverse method.
#   (Во время вычисления инверсии все поля, которые используют указанную инверсию, защищены, что означает, что они не могут быть вычислены, даже если их значение не находится в кеше.
#
#   Если к любому из этих полей обращаются и его значение отсутствует в кеше, ORM просто вернет для этих полей значение по умолчанию False.
#   Это означает, что значение инверсных полей (кроме поля, запускающего инверсный метод) может не давать своего правильного значения,
#   и это, вероятно, нарушит ожидаемое поведение инверсного метода.)
