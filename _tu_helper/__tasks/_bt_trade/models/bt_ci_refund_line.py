from odoo import fields, models


class BtCiRefundLine(models.Model):
    _name = 'bt.ci.refund.line'
    _description = 'Ci refund line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    qty = fields.Float(string='Qty')

    uom_id = fields.Many2one(comodel_name='bt.uom')

    refund_id = fields.Many2one(comodel_name='bt.customer.invoice.refund',
                                auto_join=True)
