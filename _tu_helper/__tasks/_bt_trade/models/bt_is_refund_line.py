from odoo import fields, models


class BtIsRefundLine(models.Model):
    _name = 'bt.is.refund.line'
    _description = 'Is refund line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    qty = fields.Float(string='Qty')

    uom_id = fields.Many2one(comodel_name='bt.uom')

    refund_id = fields.Many2one(comodel_name='bt.in.stock.refund',
                                auto_join=True)
