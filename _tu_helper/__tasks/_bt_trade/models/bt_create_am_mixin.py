from odoo import fields, models


class BtCreateAmMixin(models.AbstractModel):
    _name = 'bt.create.am.mixin'
    _description = 'Create AM mixin'

    def create_am(self, date):
        am_id = self.env['bt.account.move'].create({'date': date})
        return am_id

    def create_am_line(self, debit_code: str, credit_code: str, amount: float, am: int) -> None:
        debit_id = self.env['bt.account.account'].search([('name', '=', debit_code)], limit=1).id
        credit_id = self.env['bt.account.account'].search([('name', '=', credit_code)], limit=1).id
        am_id = self.env['bt.account.move'].search([('id', '=', am)])
        am_id.line_ids = [(0, 0, {
            'debit': debit_id,
            'credit': credit_id,
            'amount': amount,
            'account_move_id': am
        })]

    def create_cor_lines(self, am: int) -> None:
        am_id = self.env['bt.account.move'].search([('id', '=', am)])
        am_line_ids = am_id.line_ids
        for am_line in am_line_ids:
            am_line.cor_account_line_ids = [
                (0, 0, {
                    'account_id': am_line.debit.id,
                    'cor_account_id': am_line.credit.id,
                    'amount': am_line.amount,
                    'am_line': am_line.id
                }),
                (0, 0, {
                    'account_id': am_line.credit.id,
                    'cor_account_id': am_line.debit.id,
                    'amount': -am_line.amount,
                    'am_line': am_line.id
                })
            ]

    def get_cor_lines(self, am: int):
        am_id = self.env['bt.account.move'].search([('id', '=', am)])
        am_lines = am_id.line_ids
        cor_line_ids = []
        for am_line in am_lines:
            cor_line_ids.extend(am_line.cor_account_line_ids.mapped('id'))

        return cor_line_ids

    def clear_am(self, am: int):
        am_id = self.env['bt.account.move'].search([('id', '=', am)])
        am_lines = am_id.line_ids
        for am_line in am_lines:
            am_line.cor_account_line_ids.unlink()
        am_lines.unlink()
        return am_id

