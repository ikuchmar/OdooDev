from odoo import fields, models


class BtAccountAccount(models.Model):
    _name = 'bt.account.account'
    _description = 'Account account'

    name = fields.Char(string='Name',
                       size=10)

    description = fields.Char(string='Description',
                             limit=100)
