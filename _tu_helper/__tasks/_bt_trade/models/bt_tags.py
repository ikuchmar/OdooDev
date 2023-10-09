from odoo import fields, models

class BtTradeTags(models.Model):
    _name = 'bt.tags'
    _description = 'Bt trade tags'

    name = fields.Char(string='Name',
                       required=True)

    color = fields.Integer(string='Color index')

    partner_ids = fields.Many2many(comodel_name='bt.partner',
                                   relation='partner_tags_rel',
                                   column1='tag_id',
                                   column2='partner_id',
                                   string='Partners')

    product_ids = fields.Many2many(comodel_name='bt.product',
                                   relation='product_tags_rel',
                                   column1='tag_id',
                                   column2='product_id',
                                   string='Products')
