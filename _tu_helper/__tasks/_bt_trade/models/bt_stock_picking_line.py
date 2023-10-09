from odoo import fields, models


class BtStockPickingLine(models.Model):
    _name = 'bt.stock.picking.line'
    _description = 'Stock picking line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    stock_picking_id = fields.Many2one(comodel_name='bt.stock.picking',
                                       auto_join=True,
                                       string='Stock picking')

    qty = fields.Float(string='Quantity')

    date = fields.Date(string='Date',
                       related='stock_picking_id.date')

    uom_id = fields.Many2one(comodel_name='bt.uom',
                             string='Uom')