from odoo import fields, models


class BtProduct(models.Model):
    _name = 'bt.product'
    _description = 'Product'

    name = fields.Char(string='Name',
                       required=True)

    tags_ids = fields.Many2many(comodel_name='bt.tags',
                                relation='product_tags_rel',
                                column1='product_id',
                                column2='tag_id',
                                string='Tags')

    basic_uom_id = fields.Many2one(comodel_name='bt.uom',
                                   string='Basic uom')

    parent_id = fields.Many2one(comodel_name='bt.product',
                                string='Parent')

    child_ids = fields.One2many(comodel_name='bt.product',
                                inverse_name='parent_id',
                                string='Children')

    category_id = fields.Many2one(comodel_name='bt.product.category',
                                  string='Category')
