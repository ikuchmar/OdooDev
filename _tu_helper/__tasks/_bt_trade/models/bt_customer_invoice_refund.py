from odoo import fields, models
from datetime import date


class BtCusromerInvoiceRefund(models.Model):
    _name = 'bt.customer.invoice.refund'
    _description = 'Customer invoice refund'
    _inherit = 'bt.create.sm.mixin'

    line_ids = fields.One2many(comodel_name='bt.ci.refund.line',
                               inverse_name='refund_id',
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

    def write(self, vals_list):
        res = super(BtCusromerInvoiceRefund, self).write(vals_list)
        if vals_list.get('state') == 'confirmed':
            self.stock_move_id = self.fill_stock_move(
                self.prepare_sm_values(self.date, self.warehouse_id.id, self.line_ids, type='invoice'),
                sm_id=self.stock_move_id.id)
        else:
            if self.state != 'confirmed':
                self.clear_sm(self.stock_move_id.id)
        if vals_list.get('date'):
            self.stock_move_id.date = res.date
        return res