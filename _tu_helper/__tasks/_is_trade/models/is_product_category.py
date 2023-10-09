from odoo import fields, models


class IsProductCategory(models.Model):
    _name = 'is.product.category'
    _description = 'Categories of products'

    name = fields.Char(string='Name',
                       required=True,
                       store=True,
                       help='Product category name')
