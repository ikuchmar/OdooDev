from odoo import fields, models

class AModel(models.Model):
    _name = 'a.model'

    records.sorted(key=lambda r: r.name)

    # --------------------
    # sorted
    # -------------------
    # Дозволяє сортувати вказаний рекордсет за певним правилом. Схоже на пайтонівську функцію
    #
    #
