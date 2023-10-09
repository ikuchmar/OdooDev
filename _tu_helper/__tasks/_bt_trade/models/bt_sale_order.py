from odoo import fields, models, api
from datetime import date


class BtSaleOrder(models.Model):
    _name = 'bt.sale.order'
    _description = 'Sale Order'

    name = fields.Char(string='Order name',
                       required=True,
                       readonly=True,
                       copy=False,
                       default='New'
                       )

    date = fields.Date(string='Order date',
                       required=True,
                       default=date.today()
                       )

    client_id = fields.Many2one(comodel_name='bt.partner',
                             string='Client',
                             )

    line_ids = fields.One2many(comodel_name='bt.sale.order.line',
                               inverse_name='sale_order_id',
                               auto_join=True,
                               string='Order lines'
                               )

    total_amount = fields.Float(string='Total amount',
                                digits=(15, 2),
                                readonly=True)

    po_so_line_id = fields.One2many(comodel_name='bt.po.line.so.line',
                                    inverse_name='so_id',
                                    string='PO SO line')

    customer_invoice_id = fields.Many2one(comodel_name='bt.customer.invoice',
                                          string='Customer invoice')

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    def _compute_ci_count(self):
        self.customer_invoice_count = self.env['bt.customer.invoice'].search_count([('sale_order_id', '=', self.id)])

    customer_invoice_count = fields.Integer(string='Customer invoices',
                                            compute='_compute_ci_count')

    def _compute_po_so_count(self):
        self.po_so_line_count = self.env['bt.po.line.so.line'].search_count([('so_id', '=', self.id)])

    po_so_line_count = fields.Integer(string='PO/SO',
                                      compute='_compute_po_so_count')

    @api.model
    def create(self, vals_list):
        if vals_list.get('name', 'New') == 'New':
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.sale.order.sequence') or 'New'

        res = super(BtSaleOrder, self).create(vals_list)
        return res

    def write(self, vals):
        res = super(BtSaleOrder, self).write(vals)

        if vals.get('line_ids'):
            self.total_amount = sum(self.line_ids.mapped('amount'))

        return res

    @api.model
    def create_ci(self, id):
        order_id = self.env['bt.sale.order'].search([('id', '=', id[0])])
        vals = {
            'sale_order_id': order_id.id,
            'client_id': order_id.client_id.id,
            'total_amount': order_id.total_amount,
            'warehouse_id': order_id.warehouse_id.id
        }

        line_values = []

        for line in order_id.line_ids:
            ci_line = {
                'product_id': line.product_id.id,
                'qty': line.quantity,
                'date': date.today(),
                'uom_id': line.uom_id.id,
                'price': line.price,
                'amount': line.amount,
                'coeff_uom': line.coeff_uom,
                'qty_basic_uom': line.qty_basic_uom,
                'product_basic_uom_id': line.product_basic_uom_id.id,
                'client_id': order_id.client_id.id
            }
            line_values.append((0, 0, ci_line))

        vals['line_ids'] = line_values

        return self.env['bt.customer.invoice'].create(vals)

    def get_ci(self):
        invoices = self.env['bt.customer.invoice'].search([('sale_order_id', '=', self.id)])

        tree_view = self.env.ref('_bt_trade.bt_customer_invoice_view_tree')
        form_view = self.env.ref('_bt_trade.bt_customer_invoice_view_form')

        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer invoice',
                'res_model': 'bt.customer.invoice',
                'view_mode': 'form',
                'views': [[form_view.id, 'form']],
                'res_id': invoices.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Customer invoices',
                'res_model': 'bt.customer.invoice',
                'view_mode': 'tree,form',
                'views': [[tree_view.id, 'tree'], [form_view.id, 'form']],
                'domain': [('id', 'in', invoices.ids)],
            }

    def get_po_so(self):
        po_so_ids = self.env['bt.po.line.so.line'].search([('so_id', '=', self.id)])

        tree_view = self.env.ref('_bt_trade.bt_po_line_so_line_view_tree')
        form_view = self.env.ref('_bt_trade.bt_po_line_so_line_view_form')

        return {
            'type': 'ir.actions.act_window',
            'name': 'PO/SO',
            'res_model': 'bt.po.line.so.line',
            'view_mode': 'tree,form',
            'views': [[tree_view.id, 'tree'], [form_view.id, 'form']],
            'domain': [('id', 'in', po_so_ids.ids)],
        }
