from odoo import fields, models


class BtWarehouse(models.Model):
    _name = 'bt.warehouse'
    _description = 'Warehouse'

    name = fields.Char(string='Name')
