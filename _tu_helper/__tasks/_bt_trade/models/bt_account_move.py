from odoo import fields, models, api


class BtAccountMove(models.Model):
    _name = 'bt.account.move'
    _description = 'Account move'

    name = fields.Char(string='Name')

    date = fields.Date(string='Date')

    line_ids = fields.One2many(comodel_name='bt.account.move.line',
                               inverse_name='account_move_id',
                               string='Lines',
                               auto_join='True')

    cor_line_ids = fields.One2many(comodel_name='bt.account.cor.line',
                                   inverse_name='account_move_id',
                                   string='Cor lines',
                                   auto_join=True)

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.ac.sequence') or 'New'

        res = super(BtAccountMove, self).create(vals_list)
        return res