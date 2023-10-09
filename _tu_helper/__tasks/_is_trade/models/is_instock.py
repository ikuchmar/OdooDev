from transliterate.utils import _

from odoo import fields, models, api
from odoo.exceptions import UserError


class InStock(models.Model):
    _name = "is.instock"
    _description = "Instock"

    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    purchase_order_id = fields.Many2one('is.trade.purchase.order')
    partner = fields.Many2one('is.trade.partner')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                store=True)
    sequence = fields.Integer(string='Sequence',
                              default=1)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('new', 'New'),
        ('completed', 'Completed')
    ], default='draft')
    payment_supplier_count = fields.Integer(string='Payment Supplier Count',
                                   compute='_compute_payment_supplier_count')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('is.sequence') or _('New')
        return super(InStock, self).create(vals)

    @api.model
    def create_payment_supplier(self, id):
        instock_id = self.env['is.instock'].search([('id', '=', id[0])])
        vals = {
            'partner': instock_id.partner.id,
            'instock_id': instock_id.id,
            'total_amount': instock_id.total_amount
        }
        self.env['is.payment.supplier'].create(vals)

    def _compute_payment_supplier_count(self):
        for record in self:
            record.payment_supplier_count = self.env['is.payment.supplier'].search_count([('instock_id', '=', record.id)])

    def action_payment_supplier_count(self):
        return {
            'name': 'Payment supplier',
            'res_model': 'is.payment.supplier',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('instock_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }