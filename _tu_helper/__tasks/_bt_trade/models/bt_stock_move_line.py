from odoo import fields, models, api


class BtStockMoveLine(models.Model):
    _name = 'bt.stock.move.line'
    _description = ' Stock move line'

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    date = fields.Date(string='Date',
                       related='stock_move_id.date')

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')

    qty = fields.Float(string='Quantity')

    uom_id = fields.Many2one(comodel_name='bt.uom',
                             string='Uom')

    ci_id = fields.Many2one(comodel_name='bt.customer.invoice',
                            string='Ci')

    is_id = fields.Many2one(comodel_name='bt.in.stock',
                            string='Is')

    purchase_price = fields.Float(string='Purchase price',
                                  default=0,
                                  compute='_compute_purchase_price')

    price = fields.Float(string='Sale price',
                         default=0,
                         compute='_compute_price')

    profit = fields.Float(string='Profit',
                          compute='_compute_profit',
                          store=True)

    purchase_amount = fields.Float(string='Purchase Amount',
                                   compute='_compute_purchase_amount',
                                   store=True)

    sell_amount = fields.Float(string='Sell amount',
                               compute='_compute_amount')

    # coeff_uom = fields.Integer(string='Coefficient')

    # qty_basic_uom = fields.Float(string='Basic uom qty')

    # product_basic_uom_id = fields.Many2one(comodel_name='bt.uom',
    #                                        related='product_id.basic_uom_id',
    #                                        string='Product basic uom')

    stock_move_id = fields.Many2one(comodel_name='bt.stock.move',
                                    auto_join=True,
                                    string='Stock move')

    # stock_picking_line_id = fields.Many2one(comodel_name='bt.stock.picking.line',
    #                                         auto_join=True,
    #                                         string='Stock picking line')

    @api.depends('is_id')
    def _compute_purchase_price(self):
        for line in self:
            if line.is_id:
                line.purchase_price = \
                line.is_id.line_ids.filtered(lambda is_line: is_line.product_id.id == line.product_id.id)[0].price
            else:
                line.purchase_price = 0

    @api.depends('ci_id')
    def _compute_price(self):
        for line in self:
            if line.ci_id:
                line.price = line.ci_id.line_ids.filtered(lambda ci_line: ci_line.product_id.id == line.product_id.id)[
                    0].price
            else:
                line.price = 0

    @api.depends('purchase_amount', 'sell_amount')
    def _compute_profit(self):
        for line in self:
            if line.ci_id:
                line.profit = line.sell_amount
            else:
                line.profit = -line.purchase_amount

    @api.depends('qty', 'price')
    def _compute_amount(self):
        for line in self:
            if line.ci_id or line.price:
                line.sell_amount = -line.qty * line.price
            else:
                line.sell_amount = 0

    @api.depends('qty', 'purchase_price')
    def _compute_purchase_amount(self):
        for line in self:
            if line.is_id or line.purchase_price:
                line.purchase_amount = line.qty * line.purchase_price
            else:
                line.sell_amount = 0
