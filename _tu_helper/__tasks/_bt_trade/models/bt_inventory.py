from odoo import fields, models
from datetime import date


class BtInventory(models.Model):
    _name = 'bt.inventory'
    _description = 'Inventory'
    _inherit = 'bt.create.sm.mixin'

    line_ids = fields.One2many(comodel_name='bt.inventory.line',
                               inverse_name='inventory_id',
                               auto_join=True,
                               string='Products')

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    date = fields.Date(string='Date',
                       default=date.today())

    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             default='draft')

    stock_move_id = fields.Many2one(comodel_name='bt.stock.move',
                                    string='Stock move')

    stock_move_line_ids = fields.One2many(related='stock_move_id.line_ids')

    def make_inventory(self):
        self.stock_move_id = self.env['bt.stock.move'].create({'date': self.date})
        for line in self.line_ids:
            current_qty = sum(self.env['bt.stock.move.line'].search(
                [('product_id.id', '=', line.product_id.id),
                 ('warehouse_id.id', '=', self.warehouse_id.id)]).mapped('qty'))
            diff_qty = line.qty - current_qty
            self.add_line(self.stock_move_id.id, self.warehouse_id.id, line.product_id.id, diff_qty, line.uom_id.id)
        self.state = 'confirmed'

    def cancel_inventory(self):
        self.state = 'draft'
        self.clear_sm(self.stock_move_id.id)
