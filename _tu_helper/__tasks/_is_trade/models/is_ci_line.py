from odoo import models, fields


class CustomerInvoiceLine(models.Model):
    _name = 'is.ci.line'
    _description = 'Customer invoice lines'

    product_id = fields.Many2one(comodel_name='is.trade.product',
                                 string='Product')
    quantity = fields.Float(string='Quantity')
    ci_id = fields.Many2one(comodel_name='bt.customer.invoice')
    date = fields.Date(related='invoice_id.date')
    uom_id = fields.Many2one(comodel_name='is.trade.uom',
                             string='Units of Measure',
                             required=True)
    price = fields.Float(string='Price',
                         digits=(15, 3))
    amount = fields.Float(string='Amount',
                          digits=(15, 2))
    coef_uom = fields.Integer(string='UOM Coefficient',
                              digits=4)
    quantity_basic_uom = fields.Float(string='Basic uom quantity')
    client_id = fields.Many2one(comodel_name='is.trade.partner',
                                related='invoice_id.customer')
    invoice_id = fields.Many2one(comodel_name='is.customer.invoice')

