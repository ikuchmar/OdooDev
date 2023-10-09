from odoo import fields, models


class BtPoSoLinesWizard(models.TransientModel):
    _name = 'bt.po.so.lines.wizard'
    _description = 'Po/So lines wizard'

    product_id = fields.Many2one(comodel_name='bt.product',
                                 string='Product')
    so_id = fields.Many2one(comodel_name='bt.sale.order',
                            string='Sale order')
    so_line_id = fields.Many2one(comodel_name='bt.sale.order.line',
                                 string='Sale order line')

    from_date = fields.Date(string='From date')
    to_date = fields.Date(string='To date')

    def _get_so_po_domain(self):
        so_domain, po_domain, unlink_domain = [], [], []

        so_domain.append(('date', '!=', False))
        po_domain.append(('date', '!=', False))

        if self.product_id:
            so_domain.append(('product_id.id', '=', self.product_id.id))
            po_domain.append(('product_id.id', '=', self.product_id.id))
            unlink_domain.append(('product_id.id', '=', self.product_id.id))
        if self.so_id:
            so_domain.append(('sale_order_id', '=', self.so_id))
            unlink_domain.append(('so_id.id', '=', self.so_id))
        if self.so_line_id:
            so_domain.append(('id', '=', self.so_line_id.id))
            unlink_domain.append(('so_line_id.id', '=', self.so_line_id.id))
        if self.from_date:
            so_domain.append(('date', '>', self.from_date))
            po_domain.append(('date', '>', self.from_date))
        if self.to_date:
            so_domain.append(('date', '<', self.to_date))
            po_domain.append(('date', '<', self.to_date))

        return so_domain, po_domain, unlink_domain

    def _get_so_po_list(self, so_domain, po_domain):
        recs_so_lines = self.env['bt.sale.order.line'].search(so_domain)
        recs_po_lines = self.env['bt.purchase.order.line'].search(po_domain)

        lst_so_lines = []
        lst_po_lines = []

        for line in recs_so_lines:
            lst_so_lines.append(
                dict(product_id=line.product_id,
                     line_id=line,
                     qty=line.qty_basic_uom,
                     date=line.date)
            )
        for line in recs_po_lines:
            lst_po_lines.append(
                dict(product_id=line.product_id,
                     line_id=line,
                     qty=line.qty_basic_uom,
                     date=line.date)
            )

        return lst_so_lines, lst_po_lines

    def action_create(self):
        so_domain, po_domain, unlink_domain = self._get_so_po_domain()

        if self.env['bt.po.line.so.line'].search(unlink_domain):
            self.env['bt.po.line.so.line'].search(unlink_domain).sudo().unlink()

        lst_so_lines, lst_po_lines = self._get_so_po_list(so_domain, po_domain)

        lst_so_lines.sort(key=lambda r: r['date'])
        lst_po_lines.sort(key=lambda r: r['date'])

        for so_line in lst_so_lines:
            for po_line in lst_po_lines:
                if so_line['product_id'] != po_line['product_id']:
                    continue
                if po_line['qty'] <= 0 or so_line['qty'] <= 0:
                    continue
                if so_line['qty'] < po_line['qty']:
                    qty_write_off = so_line['qty']
                else:
                    qty_write_off = po_line['qty']
                vals = {
                    'product_id': so_line['product_id'].id,
                    'so_line_id': so_line['line_id'].id,
                    'po_line_id': po_line['line_id'].id,
                    'qty': qty_write_off
                }
                self.env['bt.po.line.so.line'].create(vals)
                po_line['qty'] -= qty_write_off
                so_line['qty'] -= qty_write_off
