from odoo import fields, models, api


class IsPurchaseOrderLine(models.Model):
    _name = 'is.trade.purchase.order.line'
    _description = 'Purchase order line'

    product_id = fields.Many2one(comodel_name='is.trade.product',
                                 string='Product',
                                 required=True)
    purchase_order_id = fields.Many2one(comodel_name='is.trade.purchase.order')
    date = fields.Date(related='purchase_order_id.date')
    quantity = fields.Float(string='Quantity',
                            required=True)
    uom_id = fields.Many2one(comodel_name='is.trade.uom',
                             string='Units of Measure',
                             required=True)
    price = fields.Float(string='Price',
                         digits=(15, 3))
    amount = fields.Float(string='Amount',
                          digits=(15, 2),
                          compute='_compute_amount',
                          store=True)
    coef_uom = fields.Integer(string='UOM Coefficient', digits=4)
    quantity_basic_uom = fields.Float(string='Basic uom quantity',
                                      store=True)
    partner_id = fields.Many2one(comodel_name='is.trade.partner',
                                  related='purchase_order_id.partner',
                                  store=True)

    @api.depends('price', 'coef_uom', 'quantity')
    def _compute_amount(self):
        for line in self:
            line.quantity_basic_uom = line.coef_uom * line.quantity
            line.amount = line.quantity_basic_uom * line.price
