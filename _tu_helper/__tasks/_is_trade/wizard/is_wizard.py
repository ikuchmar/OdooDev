from odoo import fields, models, api
from odoo.exceptions import UserError


class MarketingWizard(models.TransientModel):
    _name = 'is.po_so_wizard'
    _description = 'PO-SO Wizard'

    product_id = fields.Many2one('is.trade.product', string='Product')
    start_date = fields.Date('Start date')
    end_date = fields.Date('End date')
    sale_order = fields.Many2one('is.trade.sales.order', string='Sale Order')
    so_line = fields.Many2one('is.trade.sales.order.line', string='Sale Order Line')

    def filter_check(self):
        domain = []
        unlink_domain = []
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
            unlink_domain.append(('so_product_id', '=', self.product_id.id))
        if self.start_date:
            domain.append(('date', '>', self.start_date))
            unlink_domain.append(('so_line_id.date', '>', self.start_date))
        if self.end_date:
            domain.append(('date', '<', self.end_date))
            unlink_domain.append(('so_line_id.date', '<', self.end_date))
        so_domain = domain
        if self.so_line:
            so_domain.append(('id', '=', self.so_line.id))
            unlink_domain.append(('so_line_id.id', '=', self.so_line.id))
        if self.sale_order:
            so_domain.append(('sales_order_id', '=', self.sale_order.id))
            unlink_domain.append(('so_id.id', '=', self.so_line.id))
        return domain, so_domain, unlink_domain

    def create_list(self, domain, is_so_list=True):
        list_for_line = []
        if is_so_list:
            lines_ids = self.env['is.trade.sales.order.line'].search(domain)
        else:
            lines_ids = self.env['is.trade.purchase.order.line'].search(domain)
        for line in lines_ids:
            vals = {
                'product_id': line.product_id,
                'id': line.id,
                'quantity': line.quantity_basic_uom,
                'date': line.date
            }
            list_for_line.append(vals)
        return list_for_line

    def quantity_distribution(self):
        domain, so_domain, unlink_domain = self.filter_check()

        if so_domain:
            so_po_to_unlink = self.env['is.po.so.lines'].search(unlink_domain)
        else:
            so_po_to_unlink = self.env['is.po.so.lines'].search([])
        so_po_to_unlink.sudo().unlink()

        list_so_line = self.create_list(so_domain, is_so_list=True)
        list_po_line = self.create_list(domain, is_so_list=False)

        for so_line in list_so_line:
            qty_balans = so_line['quantity']
            for po_line in list_po_line:
                if po_line['product_id'] != so_line['product_id']:
                    continue
                if po_line['quantity'] == 0 or qty_balans == 0:
                    continue
                elif qty_balans < po_line['quantity']:
                    qty_write_off = qty_balans
                else:
                    qty_write_off = po_line['quantity']
                vals = {
                    'so_line_id': so_line['id'],
                    'po_line_id': po_line['id'],
                    'quantity': qty_write_off
                }
                self.env['is.po.so.lines'].create(vals)
                po_line['quantity'] -= qty_write_off
                qty_balans -= qty_write_off
