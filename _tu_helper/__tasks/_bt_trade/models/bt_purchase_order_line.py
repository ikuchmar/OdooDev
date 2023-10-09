from odoo import fields, models, api


class BtPurchaseOrderLine(models.Model):
    _name = 'bt.purchase.order.line'
    _description = 'Purchase order line'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product',
                                 required=True)

    quantity = fields.Float(string='Quantity')

    purchase_order_id = fields.Many2one(comodel_name='bt.purchase.order',
                                        auto_join=True,
                                        string='Purchase Order'
                                        )

    date = fields.Date(related='purchase_order_id.date')

    uom_id = fields.Many2one(comodel_name='bt.uom',
                             string='Uom')

    price = fields.Float(string='Price',
                         digits=(15, 3))

    amount = fields.Float(string='Amount',
                          digits=(15, 2),
                          store=True,
                          compute='_compute_amount',
                          readonly=True)

    coeff_uom = fields.Integer(string='Uom coefficient',
                               digits=4)

    qty_basic_uom = fields.Float(string='Basic uom quantity',
                                 store=True,
                                 # compute='_compute_qty_basic_uom',
                                 readonly=True)

    product_basic_uom_id = fields.Many2one(comodel_name='bt.uom',
                                           string='Product basic uom',
                                           related='product_id.basic_uom_id',
                                           readonly=True)

    supplier_id = fields.Many2one(comodel_name='bt.partner',
                                  related='purchase_order_id.supplier_id',
                                  store=True)

    # @api.onchange('coeff_uom', 'quantity')
    # def _qty_basic_uom(self):
    #     for line in self:
    #         line.qty_basic_uom = line.coeff_uom * line.quantity

    @api.depends('quantity', 'price', 'coeff_uom')
    def _compute_amount(self):
        for line in self:
            line.qty_basic_uom = line.coeff_uom * line.quantity
            line.amount = line.qty_basic_uom * line.price
