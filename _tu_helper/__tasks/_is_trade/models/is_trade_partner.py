from odoo import fields, models


class IsTradePartner(models.Model):
    _name = 'is.trade.partner'
    _description = 'new test field'

    name = fields.Char(string='Name',
                       required=True,
                       store=True,
                       help='Partner name')
    parent_id = fields.Many2one(comodel_name='is.trade.partner',
                                string='Parent')
    child_ids = fields.One2many(comodel_name='is.trade.partner',
                                inverse_name='parent_id',
                                string='Children')
    tags_ids = fields.Many2many(comodel_name='is_trade.tags',
                                relation='partner_table_rel',
                                string='Tags')
    partner_img = fields.Image('Partner image')
    category_id = fields.Many2one(comodel_name='is.partner.category',
                                  string='Category')
