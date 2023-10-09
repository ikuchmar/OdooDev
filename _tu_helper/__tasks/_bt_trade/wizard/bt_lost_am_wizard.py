from odoo import fields, models, api


class BtLostAmWizard(models.TransientModel):
    _name = 'bt.lost.am.wizard'
    _description = 'Delete lost account moves'

    lost_move_ids = fields.Many2many(comodel_name='bt.account.move',
                                     string='Lost account moves')
                                     # compute='check_lost')

    # @api.depends()
    def check_lost(self):
        all_moves = self.env['bt.account.move'].search([])
        linked_moves = self.env['bt.customer.invoice'].search([('account_move_id', '!=', False)]).mapped('account_move_id')
        lost_moves_ids = all_moves - linked_moves
        lost_moves_ids = lost_moves_ids.mapped('id')
        self.lost_move_ids = [(6, 0, lost_moves_ids)]

    def delete_lost_moves(self):
        self.check_lost()
        self.lost_move_ids.unlink()

