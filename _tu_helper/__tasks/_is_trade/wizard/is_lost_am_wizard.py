from odoo import fields, models, api


class IsLostAmWizard(models.TransientModel):
    _name = 'is.lost.am.wizard'
    _description = 'Find and delete lost account moves'

    # we can't connect TransientModel and Model using o2m that's why we need m2m
    am_without_ci_ids = fields.Many2many(comodel_name='is.account.move',
                                         relation='lost_am_table_rel',
                                         column1='is_trade_tags_id',
                                         column2='is_trade_partner_id',
                                         string='Account move without CI')
    aml_without_am_ids = fields.Many2many(comodel_name='is.account.move.line',
                                          relation='lost_am_line_table_rel',
                                          string='Account move lines without AM')

    def find_lost_am(self):
        am_with_ci = self.env['is.customer.invoice'].search([('account_move_id', '!=', False)]).mapped(
            'account_move_id')
        am_without_ci_ids = self.env['is.account.move'].search([('id', 'not in', am_with_ci.ids)]).ids
        self.am_without_ci_ids = [(6, 0, am_without_ci_ids)]
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'is.lost.am.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def delete_lost_moves(self):
        self.find_lost_am()
        for lost_am in self.am_without_ci_ids:
            self.write({
                "am_without_ci_ids": [(2, lost_am.id)]
            })
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'is.lost.am.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def find_lost_aml(self):
        aml_without_am = self.env['is.account.move.line'].search([
            ('account_move_id', '=', False),
        ]).ids
        self.aml_without_am_ids = [(6, 0, aml_without_am)]
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'is.lost.am.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def delete_lost_move_lines(self):
        self.find_lost_aml()
        for lost_aml in self.aml_without_am_ids:
            self.write({
                "aml_without_am_ids": [(2, lost_aml.id)]
            })
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'is.lost.am.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
