from odoo import fields, models, api

class AModel(models.Model):
    _name = 'a.model'

    # read = self.env['acount.move'].read_group(
    #   [('journal_id', '=', self.id), ('to_check', '=', True)],
    #   ['amount_total'], 'journal_id', lazy=False)

    # @api.model
    # def read_group(self, domain, fields, groupby, offset=0,
    #                limit=None, orderby=False, lazy=True):

    # --------------------
    # read_group
    # -------------------
    # Повертає словник зі список словників, дані вибірки в якому згруповані за вказаними полями.
    # domain - домен пошуку
#
# fields - список полів, елементи в списку можуть відповідати назві поля (і буде використана агрегаційна функція за замовчуванням - зазвичай це sum), field:agg або name:agg(field). У другому випадку саме значення name буде ключом
#
# groupby - список полів, за якими буде проводитись групування
#
# offset (int) – кількість рядків від початку вибірки, що буде проігнорована, для сторінкової обробки
#
# limit (int) – обмеження по кількості рядків
#
# orderby (str) – правило сортування, назви полів та порядок desc або asc (другий за замовчанням)
#
# lazy - якщо True, то групування буде здійснено лише по першому полу, а інші - переміщені в ключ __context.