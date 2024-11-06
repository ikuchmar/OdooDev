import logging

from odoo import api, models, fields
from datetime import datetime

_logger = logging.getLogger(__name__)


class YourRelatedModel(models.TransientModel):
    _name = 'mo_accounting_tools.temp_update_acc_acc_in_am_line_wizard_line'
    _description = 'Your Related Model Description'

    # name = fields.Char('Name')
    am_line_id = fields.Many2one(string='AM line',
                                 comodel_name='account.move.line',
                                 )
    am_line_id_id = fields.Integer(string='move_id',
                                   related='am_line_id.id',
                                   )

    move_id = fields.Many2one(string='move_id',
                              comodel_name='account.move',
                              )
    # move_id = fields.Many2one(string='move_id',
    #                           related='am_line_id.move_id',
    #                           )

    move_id_id = fields.Integer(string='move_id',
                                related='am_line_id.move_id.id',
                                )

    wizard_id = fields.Many2one(string='Wizard',
                                comodel_name='mo_accounting_tools.temp_update_acc_acc_in_am_line_wizard',
                                )

    def action_open_am(self):
        self.ensure_one()
        return {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.move_id_id,
        }

    def action_open_am_line(self):
        self.ensure_one()
        return {
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.am_line_id_id,
            }


class TempUpdateAccAccInAmLineWizard(models.TransientModel):
    _name = 'mo_accounting_tools.temp_update_acc_acc_in_am_line_wizard'
    _description = 'temp_update_acc_acc_in_am_line_wizard'

    version_id = fields.Char(string='Version',
                             default='v1.7',
                             )

    account_id = fields.Many2one(string='Account Account',
                                 comodel_name='account.account',
                                 domain="[('code', 'in', ['947000'])]",
                                 default=lambda self: self.env['account.account'].search(
                                     [('code', '=', 947000)]))

    account_id_new = fields.Many2one(string='Account Account (new)',
                                     comodel_name='account.account',
                                     domain="[('code', 'in', ['281000','281100','281200'])]",
                                     default=lambda self: self.env['account.account'].search(
                                         [('code', '=', 281000)]))

    journal_id = fields.Many2one(string='Account journal',
                                 comodel_name='account.journal',
                                 default=lambda self: self.env['account.journal'].browse(8)
                                 )

    date_start = fields.Date(string='Date from',
                             default=lambda self: datetime.now().replace(day=1, hour=0, minute=0, second=0))

    date_finish = fields.Date(string='Date to',
                              default=fields.Date.today())

    limit_rec = fields.Integer(string='limit',
                               default=200,
                               )

    line_ids = fields.One2many(string='Lines',
                               comodel_name='mo_accounting_tools.temp_update_acc_acc_in_am_line_wizard_line',
                               inverse_name='wizard_id',
                               )

    # logs = fields.Text(string='Text',
    #                    default="",
    #                    help='This is Text field',
    #                    )


    # =======================================================
    def button_update_am_line_by_account_account(self):
        self._update_am_line_by_account_account(self.date_start, self.date_finish, self.account_id, self.account_id_new,
                                                self.journal_id, self.limit_rec)

        # открыть форму wizard
        return {
            'context': self.env.context,
            # 'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mo_accounting_tools.temp_update_acc_acc_in_am_line_wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'date_start': self.date_start,
            'date_finish': self.date_finish,
            'account_id': self.account_id,
            'account_id_new': self.account_id_new,
            'journal_id': self.journal_id,
            'limit_rec': self.limit_rec,
            # 'logs': self.logs,
            'line_ids': self.line_ids,
        }

    # ========================================
    # def cron_update_am_line_by_analytic_account(self, date_start, date_finish, analytic_account_id, limit_rec,
    #                                             is_update_account, is_only_8_9_account):
    #     # info_str = f"я запустился"
    #     # _logger.info(info_str)
    #
    #     if not date_start:
    #         from datetime import datetime
    #         date_start = datetime(2023, 1, 1, 0, 0, 0)
    #
    # account_id = self.env['account.account'].search([('code', '=', '947000')], limit=1)

    #     self._update_am_line_by_account_account(self, date_start, date_finish, account_id, account_id_new, journal_id,
    #                                        limit_rec)

    # =======================================================
    def _update_am_line_by_account_account(self, date_start, date_finish, account_id, account_id_new, journal_id,
                                           limit_rec):

        if not account_id or not account_id_new:
            return

        domen_list = [('account_id', '=', account_id.id),
                      ('journal_id', '=', journal_id.id),
                      ('temp_account_id', '=', False),
                      ('date', '>=', date_start),
                      ]
        if date_finish:
            domen_list.append(('date', '<=', date_finish))

        account_move_line_records = self.env['account.move.line'].search(domen_list,
                                                                         order='date',
                                                                         limit=limit_rec)

        new_lines_list = []

        self.line_ids.unlink()
        # self.logs = ""
        total_ind = len(account_move_line_records)
        ind = 0
        for record_am_line in account_move_line_records:
            ind += 1
            vals = {}

            str_log = f"Обр. {ind} из {total_ind} {record_am_line}"

            _logger.info(str_log)

            # self.logs = f"{self.logs} \n {str_log}"

            new_line = {
                'wizard_id': self.id,
                'am_line_id': record_am_line.id,
                'move_id': record_am_line.move_id.id,
            }

            new_lines_list.append(new_line)

            vals['account_id'] = account_id_new.id

            # заполним поле - какой был старый бух счет
            if not record_am_line.temp_account_id:
                vals['temp_account_id'] = record_am_line.account_id.id

            # if len(vals) > 0:
            #     record_am_line.with_context(
            #         skip_invoice_sync=True,
            #         skip_invoice_line_sync=True,
            #         skip_account_move_synchronization=True,
            #         check_move_validity=False,
            #     ).write(vals)

        # am_without_ci_ids = self.env['is.account.move'].search([('id', 'not in', am_with_ci.ids)]).ids
        # self.line_ids = [(6, 0, new_lines_list)]

        self.line_ids.create(new_lines_list)
        a = 1
