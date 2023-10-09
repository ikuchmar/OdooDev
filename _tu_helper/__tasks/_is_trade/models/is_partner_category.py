from odoo import fields, models


class IsPartnerCategory(models.Model):
    _name = 'is.partner.category'
    _description = 'Categories of partners'

    name = fields.Char(string='Name',
                       required=True,
                       store=True,
                       help='Partner category name')
