from transliterate.utils import _

from odoo import fields, models, api


class IsAccountMove(models.Model):
    _name = "is.account.move"
    _description = "Account Move"

    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    # customer_invoice = fields.Many2one('is.customer.invoice')
    account_move_line_ids = fields.One2many('is.account.move.line',
                               inverse_name='account_move_id')
    # cor_line_ids = fields.One2many(comodel_name='is.account.cor.line',
    #                                inverse_name='move_id',
    #                                string='Correspodence lines',
    #                                auto_join=True)
    sequence = fields.Integer(string='Sequence',
                              default=1)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('am.sequence') or _('New')
        return super(IsAccountMove, self).create(vals)
