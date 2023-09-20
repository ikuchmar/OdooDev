from odoo import fields, models

class AModel(models.Model):
    _name = 'a.model'

    def do_operation(self):
        print(self)# =>a.model(1,2,3,4,5)
        for record in self:
            record.name="Bob"
            print(record)# => a.model(1), then a.model(2), then a.model(3),...

# --------------------
# Ітерації рекордсетів
# --------------------
# Ітерація рекордсету - це найуніверсальніший спосіб отримати рекордсет з одним записом,
# у якому можна звертатись до полів