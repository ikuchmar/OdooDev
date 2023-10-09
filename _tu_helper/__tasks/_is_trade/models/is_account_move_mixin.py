from transliterate.utils import _

from odoo import fields, models, api


class IsAccountMoveMixin(models.AbstractModel):
    _name = "is.account.move.mixin"
    _description = "Account Move Mixin"

    @api.model
    def create_account_move(self, vals):
        return self.env['is.account.move'].create(vals)

    def create_account_move_line(self, data, debet, credit, amount, am_id):
        am = self.env['is.account.move'].search([('id', '=', am_id)])
        am.account_move_line_ids = [(0, 0, self._prepare_dict(data, debet, credit, amount, am_id))]

    def _prepare_dict(self, date, debet, credit, amount, am_id):
        debet_id = self.env['is.account.account'].search([('code', '=', debet)]).id
        credit_id = self.env['is.account.account'].search([('code', '=', credit)]).id
        return {
            'date': date,
            'debet': debet_id,
            'credit': credit_id,
            'amount': amount,
            'account_move_id': am_id
        }

