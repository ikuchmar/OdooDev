from odoo import fields, models


class BtAccountCorLine(models.Model):
    _name = 'bt.account.cor.line'
    _description = 'Account cor line'

    account_id = fields.Many2one(comodel_name='bt.account.account',
                                 string='Account')

    cor_account_id = fields.Many2one(comodel_name='bt.account.account',
                                     string='Cor account')

    amount = fields.Float(string='Amount')

    account_move_id = fields.Many2one(comodel_name='bt.account.move',
                                      related='am_line.account_move_id',
                                      string='Account move',
                                      auto_join='True')

    am_line = fields.Many2one(comodel_name='bt.account.move.line',
                              string='Am line',
                              auto_join='True')
