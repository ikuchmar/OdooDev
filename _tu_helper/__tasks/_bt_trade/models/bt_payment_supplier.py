from odoo import models, fields


class BtPaymentSupplier(models.Model):
    _name = 'bt.payment.supplier'
    _description = 'Payment supplier'

    name = fields.Char(string='Name')

    partner_id = fields.Many2one(comodel_name='bt.partner',
                                 string='Partner')

    po_id = fields.Many2one(comodel_name='bt.purchase.order',
                            string='Purchase order')

    total_amount = fields.Float(string='Total amount')
