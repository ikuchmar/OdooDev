   invoice_count = fields.Integer(string='Invoice Count', compute='_get_invoiced', readonly=True)
   invoice_ids = fields.Many2many("account.move", string='Invoices', compute="_get_invoiced", readonly=True, copy=False, search="_search_invoice_ids")


   @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)
