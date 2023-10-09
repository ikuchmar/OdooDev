from odoo import models, fields


class BtInventoryLine(models.Model):
    _name = 'bt.inventory.line'
    _description = 'Inventory line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    qty = fields.Float(string='Qty')

    uom_id = fields.Many2one(comodel_name='bt.uom')

    inventory_id = fields.Many2one(comodel_name='bt.inventory',
                                   auto_join=True)
