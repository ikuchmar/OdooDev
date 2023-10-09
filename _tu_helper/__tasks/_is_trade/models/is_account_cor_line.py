from odoo import fields, models


class ISAccountCorLine(models.Model):
    _name = 'is.account.cor.line'
    _description = 'Account correspondence line'

    am_line = fields.Many2one(comodel_name='is.account.move.line',
                              ondelete='cascade',
                              string='Account move line')
    account_account_id = fields.Many2one(comodel_name='is.account.account',
                                         string='Account account')
    cor_account_id = fields.Many2one(comodel_name='is.account.account',
                                     string='Correspodence account')
    # move_id = fields.Many2one(comodel_name='is.account.move',
    #                           related='am_line.account_move_id',
    #                           string='Account move')
    amount = fields.Float(string='Amount')
