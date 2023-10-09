from odoo import fields, models, api


class AccountAccount(models.Model):
    _name = "is.account.account"
    _description = "Account Account"
    _rec_name = "code"

    name = fields.Char(string='Name',
                       required=True,
                       size=100)
    code = fields.Char(string='Code',
                       required=True,
                       size=10)
