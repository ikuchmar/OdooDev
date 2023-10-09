from odoo import fields, models, api
from transliterate.utils import _


class CustomerInvoice(models.Model):
    _name = 'is.customer.invoice'
    _description = 'Customer Invoice'
    _inherit = 'is.account.move.mixin'

    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)

    sales_order_id = fields.Many2one('is.trade.sales.order')
    customer = fields.Many2one('is.trade.partner')
    line_ids = fields.One2many(comodel_name='is.ci.line',
                               inverse_name='invoice_id')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                store=True)
    sequence = fields.Integer(string='Sequence',
                              default=1)
    account_move_id = fields.Many2one('is.account.move')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('post', 'Post')
    ], default='draft')
    payment_customer_count = fields.Integer(string='Payment Supplier Count',
                                            compute='_compute_payment_customer_count')
    # account_cor_line_ids = fields.Many2many(comodel_name='is.account.cor.line',
    #                                         relation='ci_account_cor_line_rel',
    #                                         string='Account cor lines')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('ci.sequence') or _('New')
        return super(CustomerInvoice, self).create(vals)

    def write(self, vals_ci):
        am_line_list = []
        # TODO передать дату при создании и проверить, если что заменить на дату ci
        if vals_ci.get('state'):
            for am_line in self.account_move_id.account_move_line_ids:
                self.account_move_id.write({
                    'account_move_line_ids': [(2, am_line.id)]
                })
        if vals_ci.get('state') == 'post':
            for rec in self:
                if not rec.account_move_id:
                    rec.account_move_id = rec.create_account_move({'date': rec.date})
                for line in rec.line_ids:
                    am_line_list.append((0, 0, self._prepare_dict(self.date, '902', '281', line.amount, rec.account_move_id.id)))
                self.create_account_move_line(self.date, '361', '702', rec.total_amount, rec.account_move_id.id)
                rec.account_move_id.account_move_line_ids = am_line_list
                # for am_line in rec.account_move_id.account_move_line_ids:
                #     self.create_cor_account_line(am_line.debet, am_line.credit, am_line)
        res = super(CustomerInvoice, self).write(vals_ci)
        return res

    @api.model
    def create_payment_customer(self, id):
        customer_invoice_id = self.env['is.customer.invoice'].search([('id', '=', id[0])])
        vals = {
            'customer': customer_invoice_id.customer.id,
            'customer_invoice_id': customer_invoice_id.id,
            'total_amount': customer_invoice_id.total_amount
        }
        self.env['is.payment.customer'].create(vals)

    def _compute_payment_customer_count(self):
        for record in self:
            record.payment_customer_count = self.env['is.payment.customer'].search_count(
                [('customer_invoice_id', '=', record.id)])

    def action_payment_customer_count(self):
        return {
            'name': 'Payment customer',
            'res_model': 'is.payment.customer',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('customer_invoice_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }
