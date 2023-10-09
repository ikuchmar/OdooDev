from odoo import fields, models


class BtPartner(models.Model):
    _name = 'bt.partner'
    _description = 'Partner'

    name = fields.Char(string='Name',
                       required=True)

    tags_ids = fields.Many2many(comodel_name='bt.tags',
                                relation='partner_tags_rel',
                                column1='partner_id',
                                column2='tag_id',
                                string='Tags')

    parent_id = fields.Many2one(comodel_name='bt.partner',
                                string='Parent')

    child_ids = fields.One2many(comodel_name='bt.partner',
                                inverse_name='parent_id',
                                string='Subordinates')

    group_id = fields.Many2one(comodel_name='bt.partner.group',
                               string='Group')