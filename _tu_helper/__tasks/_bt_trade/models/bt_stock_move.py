from odoo import fields, models, api


class BtStockMove(models.Model):
    _name = 'bt.stock.move'
    _description = 'Stock move'

    name = fields.Char(string='Name')

    date = fields.Date(string='Date')

    line_ids = fields.One2many(comodel_name='bt.stock.move.line',
                               inverse_name='stock_move_id',
                               string='Lines',
                               auto_join=True)

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.sm.sequence') or 'New'

        res = super(BtStockMove, self).create(vals_list)
        return res
