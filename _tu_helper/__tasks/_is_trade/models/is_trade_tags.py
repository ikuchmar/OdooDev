from odoo import fields, models


class Tags(models.Model):
    _name = "is_trade.tags"
    _description = "is_trade tags"

    name = fields.Char('Tag Name',
                       required=True)
    color = fields.Integer('Color Index')
    partner_ids = fields.Many2many(comodel_name='is.trade.partner',
                                   relation='partner_table_rel',
                                   column1='is_trade_tags_id',
                                   column2='is_trade_partner_id',
                                   string="Partners")
    product_ids = fields.Many2many(comodel_name='is.trade.product',
                                   relation='product_table_rel',
                                   column1='is_trade_tags_id',
                                   column2='is_trade_product_id',
                                   string="Products")
