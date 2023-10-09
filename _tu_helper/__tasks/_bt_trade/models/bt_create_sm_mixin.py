from odoo import fields, models


class BtCreateSmMixin(models.Model):
    _name = 'bt.create.sm.mixin'
    _description = 'Create stock move mixin'

    def prepare_sm_values(self, date, warehouse_id, lines, type, warehouse_dest_id=None):
        if warehouse_dest_id:
            sm_line_vals = []
            for line in lines:
                sm_line_vals.extend([
                    (0, 0, {
                        'warehouse_id': warehouse_id,
                        'date': date,
                        'product_id': line.product_id.id,
                        'qty': -line.qty,
                        'uom_id': line.uom_id.id
                    }),
                    (0, 0, {
                        'warehouse_id': warehouse_dest_id,
                        'date': date,
                        'product_id': line.product_id.id,
                        'qty': line.qty,
                        'uom_id': line.uom_id.id
                    })
                ])
        else:
            sm_line_vals = [(0, 0, {
                'warehouse_id': warehouse_id,
                'date': date,
                'product_id': line.product_id.id,
                'qty': line.qty if type == 'invoice' else -line.qty,
                'uom_id': line.uom_id.id
            }) for line in lines]
        return {
            'date': date,
            'line_ids': sm_line_vals
        }

    def fill_stock_move(self, vals, sm_id=None):
        if not sm_id:
            stock_move_id = self.env['bt.stock.move'].create(vals)
        else:
            stock_move_id = self.env['bt.stock.move'].search([('id', '=', sm_id)])
            stock_move_id.write(vals)
        return stock_move_id

    def add_line(self, sm_id, warehouse_id, product_id, qty, uom_id):
        stock_move_id = self.env['bt.stock.move'].search([('id', '=', sm_id)])
        stock_move_id.line_ids = [(0, 0, {
            'warehouse_id': warehouse_id,
            'date': stock_move_id.date,
            'product_id': product_id,
            'qty': qty,
            'uom_id': uom_id
        })]

    def clear_sm(self, sm_id):
        stock_move = self.env['bt.stock.move'].search([('id', '=', sm_id)])
        for sm_line in stock_move.line_ids:
            sm_line.unlink()
        return stock_move
