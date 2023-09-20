from odoo import fields, models, api

class CreateMethod(models.Model):
    _inherit = '_tu_helper.field'

    @api.model
    def create(self, vals):
        record = super(BasicField, self).create(vals)
        # do some additional actions
        return record

# create (не метод recordset)
# Створює нові записи та повертає їх.
# При создании объкта
# Якщо використовується з @api.model_create_multi отримує список словників та повертає рекордсет створених записів.
# Якщо використовується застаріла форма @api.model отримує словник і повертає створений об’єкт
# Поля, значення яких не були передані, будуть заповнені значеннями за замовчуванням.
#


# ==========================================================
# Метод создания записи:
# ==========================================================
# @api.model
# def create(self, vals):
#     record = super(MyModel, self).create(vals)
#     # do some additional actions
#     return record
# В этом примере мы создаем метод create в модели MyModel. Этот метод переопределяет метод create в родительской модели.
# Метод create создает новую запись в модели на основе значений, переданных в параметре vals. Затем он выполняет дополнительные действия и возвращает созданную запись.
# Важливо, якщо при виклику не були передані обов’язкові поля і вони не мають визначених значень за замовчуванням, це призвиде до помилки.

# ==========================================================
# @api.model_create_multi
# ==========================================================
# Спеціальний декоратор, для метода create.
# Після реалізації множинного створення (для збільшення швидкодії) потрібен для зворотної сумісності зі старим стилем,
# коли в create передається словник, а не список словників.
#
# @api.model_create_multi
# def create(self, values_list):
#    for values in values_list:
#        if 'acquirer_id' in values:
#            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
#
#            # Include acquirer-specific create values
#            values.update(self._get_specific_create_values(acquirer.provider, values))
#        else:
#            pass  # Let psycopg warn about the missing required field