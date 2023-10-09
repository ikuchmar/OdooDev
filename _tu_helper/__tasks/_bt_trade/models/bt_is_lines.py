from odoo import models, fields


class BtISLine(models.Model):
    _name = 'bt.is.line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    qty = fields.Float(string='Quantity')

    invoice_id = fields.Many2one(comodel_name='bt.in.stock',
                                 string='Invoice',
                                 auto_join=True)

    date = fields.Date(string='Date',
                       related='invoice_id.date')

    uom_id = fields.Many2one(comodel_name='bt.uom',
                             string='Uom')

    price = fields.Float(string='Price')

    amount = fields.Float(string='Amount')

    coeff_uom = fields.Integer(string='Coefficient')

    qty_basic_uom = fields.Float(string='Basic uom qty')

    product_basic_uom_id = fields.Many2one(comodel_name='bt.uom',
                                           related='product_id.basic_uom_id',
                                           string='Product basic uom')

    supplier_id = fields.Many2one(comodel_name='bt.partner',
                                  related='invoice_id.supplier_id',
                                  string='supplier')
