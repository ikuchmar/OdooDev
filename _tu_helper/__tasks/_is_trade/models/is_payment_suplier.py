from odoo import fields, models, api
from transliterate.utils import _


class PaymentSupplier(models.Model):
    _name = "is.payment.supplier"
    _description = "Payment Supplier"

    name = fields.Char(string='Name')
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    instock_id = fields.Many2one('is.instock')
    partner = fields.Many2one('is.trade.partner')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ps.sequence') or _('New')
        return super(PaymentSupplier, self).create(vals)