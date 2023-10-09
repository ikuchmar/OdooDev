from odoo import fields, models, api
from odoo.exceptions import UserError


class BtPOlineSOline(models.Model):
    _name = 'bt.po.line.so.line'
    _description = 'Bt PO Line SO Line'

    name = fields.Char(string='Name')

    product_id = fields.Many2one(comodel_name='bt.product',
                                 store=True)

    po_line_id = fields.Many2one(comodel_name='bt.purchase.order.line',
                                 string='Purchase order line',
                                 store=True)

    so_line_id = fields.Many2one(comodel_name='bt.sale.order.line',
                                 string='Sale order line',
                                 store=True)

    so_id = fields.Many2one(comodel_name='bt.sale.order',
                            related='so_line_id.sale_order_id',
                            store=True)

    po_id = fields.Many2one(comodel_name='bt.purchase.order',
                            related='po_line_id.purchase_order_id',
                            store=True)

    qty = fields.Integer(string='Quantity',
                         required=True,
                         store=True)

    po_cost_amount = fields.Float(string='Cost amount',
                                 compute='_compute_po_cost_price',
                                 store=True)

    so_revenue_amount = fields.Float(string='Revenue amount',
                             compute='_compute_income',
                             store=True)

    profit = fields.Float(string='Profit',
                          compute='_compute_profit',
                          store=True)

    @api.depends('po_line_id', 'qty')
    def _compute_po_cost_price(self):
        for item in self:
            item.po_cost_amount = item.po_line_id.price * item.qty

    @api.depends('so_line_id', 'qty')
    def _compute_income(self):
        for item in self:
            item.so_revenue_amount = item.so_line_id.price * item.qty

    @api.depends('po_cost_amount', 'so_revenue_amount')
    def _compute_profit(self):
        for item in self:
            item.profit = item.so_revenue_amount - item.po_cost_amount

    def write(self, vals):
        res = super(BtPOlineSOline, self).write(vals)
        if self.so_line_id.qty_basic_uom < self.qty or self.po_line_id.qty_basic_uom < self.qty:
            raise UserError('Incorrect quantity!')

        return res
