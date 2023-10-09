from odoo import models, fields, api
from datetime import date


class BtInStock(models.Model):
    _name = 'bt.in.stock'
    _description = 'In stock'

    _inherit = 'bt.create.sm.mixin'

    name = fields.Char(string='Name')

    purchase_order_id = fields.Many2one(comodel_name='bt.purchase.order',
                                        string='Purchase order')

    date = fields.Date(string='Date', default=date.today())

    supplier_id = fields.Many2one(comodel_name='bt.partner',
                                  string='Supplier')

    line_ids = fields.One2many(comodel_name='bt.is.line',
                               inverse_name='invoice_id',
                               auto_join=True,
                               string='Invoice lines')

    total_amount = fields.Float(string='Total amount',
                                readonly=True)

    state = fields.Selection(selection=[('draft', 'Draft'), ('post', 'Post')],
                             default='draft')

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    stock_move_id = fields.Many2one(comodel_name='bt.stock.move',
                                    string='Stock move')

    stock_move_line_ids = fields.One2many(related='stock_move_id.line_ids',
                                          string='Stock move lines')

    def _compute_payment_supplier_count(self):
        self.payment_supplier_count = self.env['bt.payment.supplier'].search_count(
            [('po_id', '=', self.purchase_order_id.id)])

    payment_supplier_count = fields.Integer(string='Payment supplier',
                                            compute='_compute_payment_supplier_count')

    @api.model
    def create_payment(self, id):
        is_id = self.env['bt.in.stock'].search([('id', '=', id[0])])
        vals = {
            'name': self.env['ir.sequence'].next_by_code('bt.ps.sequence') or 'New',
            'partner_id': is_id.supplier_id.id,
            'po_id': is_id.purchase_order_id.id,
            'total_amount': is_id.total_amount
        }
        self.env['bt.payment.supplier'].create(vals)

    def get_payment_supplier(self):
        payments = self.env['bt.payment.supplier'].search([('po_id', '=', self.purchase_order_id.id)])

        tree_view = self.env.ref('_bt_trade.bt_payment_supplier_view_tree')
        form_view = self.env.ref('_bt_trade.bt_payment_supplier_view_form')

        if len(payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment supplier',
                'res_model': 'bt.payment.supplier',
                'view_mode': 'form',
                'views': [[form_view.id, 'form']],
                'res_id': payments.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment supplier',
                'res_model': 'bt.payment.supplier',
                'view_mode': 'tree,form',
                'views': [[tree_view.id, 'tree'], [form_view.id, 'form']],
                'domain': [('id', 'in', payments.ids)],
            }

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.is.sequence') or 'New'

        res = super(BtInStock, self).create(vals_list)
        return res

    def write(self, vals_list):
        res = super(BtInStock, self).write(vals_list)
        if vals_list.get('state') == 'post':
            self.stock_move_id = self.fill_stock_move(
                self.prepare_sm_values(self.date, self.warehouse_id.id, self.line_ids, type='invoice'),
                sm_id=self.stock_move_id.id)
        else:
            if self.state != 'post':
                self.clear_sm(self.stock_move_id.id)
        if vals_list.get('date'):
            self.stock_move_id.date = res.date
        return res
