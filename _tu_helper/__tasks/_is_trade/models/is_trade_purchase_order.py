from transliterate.utils import _

from odoo import fields, models, api


class IsTradePurchaseOrder(models.Model):
    _name = 'is.trade.purchase.order'
    _description = 'Purchase model'

    name = fields.Char(string='Name',
                       required=True,
                       copy=False,
                       readonly=True,
                       default=lambda self: _('New'))
    date = fields.Date(required=True,
                       default=fields.Date.context_today)
    partner = fields.Many2one('is.trade.partner')
    line_ids = fields.One2many('is.trade.purchase.order.line',
                               inverse_name='purchase_order_id')
    total_amount = fields.Float(string='Amount',
                                digits=(15, 2),
                                readonly=True)
    sequence = fields.Integer(string='Sequence',
                              default=1)
    po_so_line_ids = fields.One2many(comodel_name='is.po.so.lines',
                                     inverse_name='po_id',
                                     string="Purchase and sale order lines")
    instock_count = fields.Integer(string='Instock Count',
                                   compute='_compute_instock_count')
    po_so_line_count = fields.Integer(string='PO SO Line Count',
                                      compute='_compute_po_so_line_count')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('po.sequence') or _('New')
        if vals.get('line_ids'):
            self.total_amount = sum(self.line_ids.mapped('amount'))
        return super(IsTradePurchaseOrder, self).create(vals)

    def write(self, vals):
        res = super(IsTradePurchaseOrder, self).write(vals)
        if vals.get('line_ids'):
            self.total_amount = sum(self.line_ids.mapped('amount'))
        return res

    def create_in_stock(self):
        for record in self:
            record.env['is.instock'].create({
                'partner': record.partner.id,
                'total_amount': record.total_amount,
                'purchase_order_id': record.id,
            })

    def _compute_instock_count(self):
        for record in self:
            record.instock_count = self.env['is.instock'].search_count([("purchase_order_id", "=", record.id)])

    def _compute_po_so_line_count(self):
        for record in self:
            record.po_so_line_count = self.env['is.po.so.lines'].search_count([('po_id', '=', self.id)])
    def action_instock_count(self):
        return {
            'name': 'Instock',
            'res_model': 'is.instock',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('purchase_order_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }

    def action_po_so_line_count(self):
        return {
            'name': 'PO SO line',
            'res_model': 'is.po.so.lines',
            'view_mode': 'list,form',
            'context': {},
            'domain': [('po_id', '=', self.id)],
            'target': 'current',
            'type': 'ir.actions.act_window',
        }