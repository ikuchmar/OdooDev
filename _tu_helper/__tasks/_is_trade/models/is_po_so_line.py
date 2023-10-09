from odoo import fields, models, api
from odoo.exceptions import UserError


class IsPoSoLine(models.Model):
    _name = "is.po.so.lines"
    _description = "Po lines and SO lines"

    po_line_id = fields.Many2one(comodel_name='is.trade.purchase.order.line',
                                 store=True)
    so_line_id = fields.Many2one(comodel_name='is.trade.sales.order.line',
                                 store=True)
    so_id = fields.Many2one(comodel_name='is.trade.sales.order',
                            related='so_line_id.sales_order_id',
                            store=True)
    po_id = fields.Many2one(comodel_name='is.trade.purchase.order',
                            related='po_line_id.purchase_order_id',
                            store=True)
    quantity = fields.Float(string='Quantity')
    po_amount = fields.Float(string='Cost amount',
                             compute='_compute_po_amount',
                             store=True)
    so_amount = fields.Float(string='Revenue amount',
                             compute='_compute_so_amount',
                             store=True)
    profit = fields.Float(string='Profit',
                          compute='_compute_benefit_amount',
                          store=True)
    so_quantity = fields.Float(string='SO quantity',
                               related='so_line_id.quantity_basic_uom')
    po_quantity = fields.Float(string='PO quantity',
                               related='po_line_id.quantity_basic_uom')
    po_product_id = fields.Many2one(string='PO Product',
                                    related='po_line_id.product_id')
    so_product_id = fields.Many2one(string='SO Product',
                                    related='so_line_id.product_id',
                                    store=True)

    @api.depends('po_line_id', 'quantity')
    def _compute_po_amount(self):
        for line in self:
            line.po_amount = line.po_line_id.price * line.quantity

    @api.depends('so_line_id', 'quantity')
    def _compute_so_amount(self):
        for line in self:
            line.so_amount = line.so_line_id.price * line.quantity

    @api.depends('po_amount', 'so_amount')
    def _compute_benefit_amount(self):
        for line in self:
            line.profit = line.so_amount - line.po_amount

    def write(self, vals):
        result = super(IsPoSoLine, self).write(vals)
        if self.so_line_id.quantity_basic_uom > self.quantity:
            raise UserError('wrong quantity of SO line')
        if self.po_line_id.quantity_basic_uom > self.quantity:
            raise UserError('wrong quantity of PO line')
        return result
