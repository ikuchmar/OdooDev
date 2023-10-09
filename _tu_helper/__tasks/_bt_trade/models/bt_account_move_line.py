from odoo import fields, models


class BtAccountMoveLine(models.Model):
    _name = 'bt.account.move.line'
    _description = 'Account move line'

    account_move_id = fields.Many2one(comodel_name='bt.account.move',
                                      string='Account move',
                                      auto_join='True')

    debit = fields.Many2one(comodel_name='bt.account.account',
                            string='Debit')

    credit = fields.Many2one(comodel_name='bt.account.account',
                             string='Credit')

    amount = fields.Float(string='Amount',
                          digit=(15, 2))

    date = fields.Date(string='Date',
                       relation='account_move_id.date')

    cor_account_line_ids = fields.One2many(comodel_name='bt.account.cor.line',
                                           inverse_name='am_line',
                                           string='Account cor lines',
                                           auto_join='True')
