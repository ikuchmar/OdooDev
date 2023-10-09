from transliterate.utils import _

from odoo import fields, models, api


class IsTradeSalesOrder(models.Model):
    _name = 'is.trade.sales.order'
    _description = 'SO model'
    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    client = fields.Many2one('is.trade.partner')
    line_ids = fields.One2many('is.trade.sales.order.line',
                               inverse_name='sales_order_id')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                readonly=True)
    sequence = fields.Integer(string='Sequence',
                              default=1)
    po_so_line_ids = fields.One2many(comodel_name='is.po.so.lines',
                                     inverse_name='so_id')
    customer_invoice_count = fields.Integer(string='Customer Invoice Count',
                                            compute='_compute_customer_invoice_count')
    po_so_line_count = fields.Integer(string='PO SO Line Count',
                                      compute='_compute_po_so_line_count')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('so.sequence') or _('New')
        if vals.get('line_ids'):
            self.total_amount = sum(self.line_ids.mapped('amount'))
        return super(IsTradeSalesOrder, self).create(vals)

    def write(self, vals):
        result = super(IsTradeSalesOrder, self).write(vals)
        if vals.get('line_ids'):
            self.total_amount = sum(self.line_ids.mapped('amount'))
        return result

    def create_customer_invoice(self):
        for record in self:
            vals = {
                'customer': record.client.id,
                'total_amount': record.total_amount,
                'sales_order_id': record.id,
            }
            line_values = []
            for line in record.line_ids:
                line_values.append((0, 0, self.prepare_ci_line(line)))
            vals.update({
                'line_ids': line_values,
            })
            record.env['is.customer.invoice'].create(vals)

    def prepare_ci_line(self, so_line):
        return {
            'product_id': so_line.product_id.id,
            'quantity': so_line.quantity,
            'uom_id': so_line.uom_id.id,
            'price': so_line.price,
            'amount': so_line.amount,
            'coef_uom': so_line.coef_uom,
            'quantity_basic_uom': so_line.quantity_basic_uom,
            'client_id': so_line.client_id.id,
        }

    def _compute_customer_invoice_count(self):
        for record in self:
            record.customer_invoice_count = self.env['is.customer.invoice'].search_count(
                [("sales_order_id", "=", record.id)])

    def _compute_po_so_line_count(self):
        for record in self:
            record.po_so_line_count = self.env['is.po.so.lines'].search_count([('so_id', '=', self.id)])

    def action_customer_invoice_count(self):
        return {
            'name': 'Customer Invoice',
            'res_model': 'is.customer.invoice',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('sales_order_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    def action_po_so_line_count(self):
        return {
            'name': 'PO SO line',
            'res_model': 'is.po.so.lines',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('so_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }
