from odoo import fields, models

class BtProductCategory(models.Model):
    _name = 'bt.product.category'
    _description = 'Product category'

    name = fields.Char(string='Category name',
                       required=True)