from odoo import fields, models, api


class BtSaleOrderLine(models.Model):
    _name = 'bt.sale.order.line'
    _description = 'Sale order line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product',
                                 required=True)

    quantity = fields.Float(string='Quantity')

    sale_order_id = fields.Many2one(comodel_name='bt.sale.order',
                                    auto_join=True,
                                    string='Sale Order')

    date = fields.Date(related='sale_order_id.date')

    uom_id = fields.Many2one(comodel_name='bt.uom',
                             string='Uom')

    price = fields.Float(string='Price',
                         digits=(15, 3))

    amount = fields.Float(string='Amount',
                          digits=(15, 2),
                          compute='_compute_amount',
                          readonly=True,
                          store=True)

    coeff_uom = fields.Integer(string='Uom coefficient',
                               digits=4)

    qty_basic_uom = fields.Float(string='Basic uom quantity',
                                 # compute='_compute_qty_basic_uom',
                                 readonly=True,
                                 store=True)

    product_basic_uom_id = fields.Many2one(comodel_name='bt.uom',
                                           string='Product basic uom',
                                           related='product_id.basic_uom_id',
                                           readonly=True)

    client_id = fields.Many2one(comodel_name='bt.partner',
                                  related='sale_order_id.client_id',
                                  store=True)

    # @api.onchange('coeff_uom', 'quantity')
    # def _compute_qty_basic_uom(self):
    #     for line in self:
    #         if line.coeff_uom and line.quantity:
    #             line.qty_basic_uom = line.coeff_uom * line.quantity
    #         else:
    #             line.qty_basic_uom = 0

    @api.depends('quantity', 'price', 'coeff_uom')
    def _compute_amount(self):
        for line in self:
            line.qty_basic_uom = line.coeff_uom * line.quantity
            line.amount = line.qty_basic_uom * line.price
