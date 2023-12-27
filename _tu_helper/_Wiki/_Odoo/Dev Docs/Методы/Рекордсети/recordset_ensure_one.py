from odoo import fields, models

class AModel(models.Model):
    _name = 'a.models'

    def a_method(self):
        self.ensure_one()
        self.name = "Bob"

    # --------------------
    # ensure_one
    # --------------------
    # Метод ensure_one дозволяє впевнитись, що метод працює з рекордсетом з одним записом.
    # Після виклику цього метода можна працювати з полями
    # 