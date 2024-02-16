class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    mo_if_rfq_sent = fields.Boolean(string='If RFQ sent', default=False)
    mo_if_action_rfq_sent = fields.Boolean(string='If RFQ sent', default=False)
    mo_if_action = fields.Boolean(string='If action', default=False)
    attached_purchase_req = fields.Many2one('purchase.requisition', string='Purchase Requisition')
    purchase_price = fields.Float(string='Purchase Price', group_operator=False)
    warehouse_id = fields.Many2one('stock.warehouse')
    purchase_req_discount = fields.Float('Purchase Discount', group_operator=False)
    retail_price = fields.Float('Retail Price', group_operator=False)
    difference = fields.Float('Difference', group_operator=False)
    with_action_line = fields.Boolean()
    retail_sum = fields.Float('Sum')
    order_id = fields.Many2one('sale.order', string='Sale order', related='picking_id.sale_id')
    purchase_req_payment_type = fields.Selection(
        [('deferment', 'Deferment'), ('realization', 'Realization'), ('prepayment', 'Prepayment')],
        string='Credit type')
    sold_qty = fields.Float()

    # ким ищу в какой момент заполняется поле location_dest_id - в stock.picking  таблица stock.move.line
    @api.model
    def create(self, values):
        # Добавьте свою логику или изменения перед созданием записи
        # Выполните вызов исходного метода create через super()
        move_line = super(StockMoveLine, self).create(values)
        print(f"Зашел в create {self.picking_id}")
        # Выполните необходимые действия после создания записи
        return move_line

    # ким ищу в какой момент заполняется поле location_dest_id - в stock.picking  таблица stock.move.line
    def write(self, values):
        # Добавьте свою логику или изменения перед записью
        # Выполните вызов исходного метода write через super()
        result = super(StockMoveLine, self).write(values)
        print(f"Зашел во write {self.picking_id} ")
        # Выполните необходимые действия после записи
        return result

