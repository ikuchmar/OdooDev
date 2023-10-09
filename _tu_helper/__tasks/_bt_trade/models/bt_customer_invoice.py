from odoo import fields, models, api
from datetime import date


class BtCustomerInvoice(models.Model):
    _name = 'bt.customer.invoice'
    _description = 'Customer invoice'

    _inherit = ['bt.create.am.mixin', 'bt.create.sm.mixin']

    name = fields.Char(string='Name')

    sale_order_id = fields.Many2one(comodel_name='bt.sale.order',
                                    string='Sale order')

    date = fields.Date(string='Date', default=date.today())

    client_id = fields.Many2one(comodel_name='bt.partner',
                                string='Client')

    line_ids = fields.One2many(comodel_name='bt.ci.line',
                               inverse_name='invoice_id',
                               auto_join=True,
                               string='Invoice lines')

    total_amount = fields.Float(string='Total amount',
                                readonly=True)

    state = fields.Selection(selection=[('draft', 'Draft'), ('post', 'Post')],
                             default='draft')

    account_move_id = fields.Many2one(comodel_name='bt.account.move',
                                      string='Account move')

    account_move_line_ids = fields.One2many(related='account_move_id.line_ids',
                                            string='Account move lines')

    account_cor_line_ids = fields.Many2many(comodel_name='bt.account.cor.line',
                                            string='Account cor lines')

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    stock_move_id = fields.Many2one(comodel_name='bt.stock.move',
                                    string='Stock move')

    stock_move_line_ids = fields.One2many(related='stock_move_id.line_ids',
                                          string='Stock move lines')

    def _compute_payment_customer_count(self):
        self.payment_customer_count = self.env['bt.payment.customer'].search_count(
            [('so_id', '=', self.sale_order_id.id)])

    payment_customer_count = fields.Integer(string='Payment customer',
                                            compute='_compute_payment_customer_count')

    @api.model
    def create_payment(self, id):
        ci_id = self.env['bt.customer.invoice'].search([('id', '=', id[0])])
        vals = {
            'partner_id': ci_id.client_id.id,
            'so_id': ci_id.sale_order_id.id,
            'total_amount': ci_id.total_amount
        }
        self.env['bt.payment.customer'].create(vals)

    def get_payment_customer(self):
        payments = self.env['bt.payment.customer'].search([('so_id', '=', self.sale_order_id.id)])

        tree_view = self.env.ref('_bt_trade.bt_payment_customer_view_tree')
        form_view = self.env.ref('_bt_trade.bt_payment_customer_view_form')

        if len(payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment customer',
                'res_model': 'bt.payment.customer',
                'view_mode': 'form',
                'views': [[form_view.id, 'form']],
                'res_id': payments.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Payment customer',
                'res_model': 'bt.payment.customer',
                'view_mode': 'tree,form',
                'views': [[tree_view.id, 'tree'], [form_view.id, 'form']],
                'domain': [('id', 'in', payments.ids)],
            }

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.ci.sequence') or 'New'

        res = super(BtCustomerInvoice, self).create(vals_list)

        return {
            'name': 'Customer invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'bt.customer.invoice',
            'res_id': res.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'form_view_ref': '_bt_trade.bt_customer_invoice_view_form_readonly'
            }
        }

    def write(self, vals_list):
        res = super(BtCustomerInvoice, self).write(vals_list)
        if vals_list.get('state') == 'post':
            if not self.account_move_id:
                self.account_move_id = self.create_am(self.date)
            self.create_am_line('902', '281', self.total_amount, self.account_move_id.id)
            self.create_am_line('361', '702', self.total_amount, self.account_move_id.id)
            self.create_cor_lines(self.account_move_id.id)
            cor_line_ids = self.get_cor_lines(self.account_move_id.id)
            self.account_cor_line_ids = [(6, 0, cor_line_ids)]
            self.stock_move_id = self.fill_stock_move(
                self.prepare_sm_values(self.date, self.warehouse_id.id, self.line_ids, type='outvoice'),
                sm_id=self.stock_move_id.id)
        else:
            if self.state != 'post':
                self.account_cor_line_ids.unlink()
                self.clear_am(self.account_move_id.id)
                self.clear_sm(self.stock_move_id.id)
        if vals_list.get('date'):
            self.account_move_id.date = res.date
            self.stock_move_id.date = res.date
        return res
