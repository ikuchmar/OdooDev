from odoo import fields, models, api


class IsTradeSalesOrderLine(models.Model):
    _name = 'is.trade.sales.order.line'
    _description = 'Sales order line'

    product_id = fields.Many2one(comodel_name='is.trade.product',
                                 string='Product',
                                 required=True)
    quantity = fields.Float(string='Quantity',
                            required=True)
    sales_order_id = fields.Many2one(comodel_name='is.trade.sales.order')
    date = fields.Date(related='sales_order_id.date')
    uom_id = fields.Many2one(comodel_name='is.trade.uom',
                             string='Units of Measure',
                             required=True)
    price = fields.Float(string='Price',
                         digits=(15, 3))
    amount = fields.Float(string='Amount',
                          digits=(15, 2),
                          compute='_compute_amount',
                          store=True)
    coef_uom = fields.Integer(string='UOM Coefficient',
                              digits=4)
    quantity_basic_uom = fields.Float(string='Basic uom quantity',
                                      store=True)
    client_id = fields.Many2one(comodel_name='is.trade.partner',
                                related='sales_order_id.client',
                                store=True)

    @api.depends('price', 'coef_uom', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.quantity_basic_uom = line.coef_uom * line.quantity
            line.amount = line.quantity_basic_uom * line.price

