from odoo import fields, models, api
from transliterate.utils import _


class PaymentCustomer(models.Model):
    _name = "is.payment.customer"
    _description = "Payment Customer"

    name = fields.Char(string='Name')
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    customer_invoice_id = fields.Many2one('is.customer.invoice')
    customer = fields.Many2one('is.trade.partner')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pc.sequence') or _('New')
        return super(PaymentCustomer, self).create(vals)
