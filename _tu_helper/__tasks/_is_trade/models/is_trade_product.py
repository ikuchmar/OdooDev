from odoo import fields, models


class IsTradeProduct(models.Model):
    _name = 'is.trade.product'
    _description = 'Product model'

    name = fields.Char('Product name', required=True)
    basic_uom_id = fields.Many2one('is.trade.uom')
    parent_id = fields.Many2one('is.trade.product', string='Parent')
    child_ids = fields.One2many('is.trade.product', 'parent_id', string='Children')
    tags_ids = fields.Many2many(comodel_name='is_trade.tags',
                                relation='product_table_rel',
                                string='Tags')
    product_img = fields.Image('Product image')
    category_id = fields.Many2one(comodel_name='is.product.category',
                                  string='Category')
