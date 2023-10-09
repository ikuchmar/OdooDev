from odoo import fields, models, api
import datetime


class BtStockPicking(models.Model):
    _name = 'bt.stock.picking'
    _description = 'Stock picking'

    _inherit = 'bt.create.sm.mixin'

    name = fields.Char(string='Name')

    warehouse_id = fields.Many2one(comodel_name='bt.warehouse',
                                   string='Warehouse')

    warehouse_dest_id = fields.Many2one(comodel_name='bt.warehouse',
                                        string='Dest warehouse')

    date = fields.Date(string='Date',
                       default=datetime.date.today())

    line_ids = fields.One2many(comodel_name='bt.stock.picking.line',
                               inverse_name='stock_picking_id',
                               string='Lines',
                               auto_join=True)

    state = fields.Selection(selection=[('draft', 'Draft'), ('confirmed', 'Confirmed')],
                             default='draft')

    stock_move_id = fields.Many2one(comodel_name='bt.stock.move',
                                    string='Stock move')

    stock_move_line_ids = fields.One2many(related='stock_move_id.line_ids',
                                          string='Stock move lines')

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.sp.sequence') or 'New'

        res = super(BtStockPicking, self).create(vals_list)
        return res

    def write(self, vals_list):
        res = super(BtStockPicking, self).write(vals_list)
        if vals_list.get('state') == 'confirmed':
            self.stock_move_id = self.fill_stock_move(
                self.prepare_sm_values(self.date, self.warehouse_id.id, self.line_ids, type='outvoice',
                                       warehouse_dest_id=self.warehouse_dest_id.id), sm_id=self.stock_move_id.id)
        else:
            if self.state != 'confirmed':
                self.clear_sm(self.stock_move_id.id)
        if vals_list.get('date'):
            self.stock_move_id.date = res.date
        return res
