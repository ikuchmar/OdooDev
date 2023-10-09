from odoo import fields, models

class BtPartnerGroup(models.Model):
    _name = 'bt.partner.group'
    _description = 'Partner group'

    name = fields.Char(string='Group name',
                       required=True)