from transliterate.utils import _

from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _name = "is.account.move.line"
    _description = "Account Move Lines"
    # _inherit = 'is.account.move.mixin'

    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    account_move_id = fields.Many2one(comodel_name='is.account.move')
    amount = fields.Float(string='Amount',
                          digits=(15, 2))
    debet = fields.Many2one(comodel_name='is.account.account')
    credit = fields.Many2one(comodel_name='is.account.account')
    cor_line_ids = fields.One2many(comodel_name='is.account.cor.line',
                                   inverse_name='am_line',
                                   string='Correspodence lines')

    @api.model
    def create(self, vals):
        debet = vals.get('debet')
        credit = vals.get('credit')
        amount = vals.get('amount')
        vals['cor_line_ids'] = [(0, 0, self._prepare_cor_line(debet, credit, amount)),
                                (0, 0, self._prepare_cor_line(credit, debet, -amount))]
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('aml.sequence') or _('New')
        return super(AccountMoveLine, self).create(vals)

    @api.onchange('debet', 'credit', 'amount')
    def _onchange_original_move_line_ids(self):
        self.update_cor_account_line(self.debet, self.credit, self.amount)

    # def write(self, vals):
    #     res = super(AccountMoveLine, self).write(vals)
    #     if 'debet' or 'credit' or 'amount' not in vals:
    #         debet = vals.get('debet') if vals.get('debet') else self.debet
    #         credit = vals.get('credit') if vals.get('credit') else self.credit
    #         amount = vals.get('amount') if vals.get('amount') else self.amount
    #         # self.update_cor_account_line(debet, credit, amount)
    #         # vals_list = []
    #         # for cor_line in self.cor_line_ids:
    #         #     vals_list.append((2, cor_line.id))
    #         # self.cor_line_ids = vals_list
    #         self.cor_line_ids = [(0, 0, self._prepare_cor_line(debet, credit, amount)),
    #                              (0, 0, self._prepare_cor_line(credit, debet, -amount))]
    #     return res

    def update_cor_account_line(self, debet, credit, line_amount):
        vals_list = []
        for cor_line in self.cor_line_ids:
            vals_list.append((2, cor_line.id))
        self.cor_line_ids = vals_list
        self.cor_line_ids = [(0, 0, self._prepare_cor_line(debet, credit, line_amount)),
                             (0, 0, self._prepare_cor_line(credit, debet, -line_amount))]

    def _prepare_cor_line(self, debet, credit, amount_aml):
        return {
            'account_account_id': debet,
            'cor_account_id': credit,
            'amount': amount_aml
        }
