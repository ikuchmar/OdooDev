import logging

from odoo import api, models, fields
from datetime import datetime

_logger = logging.getLogger(__name__)


class YourRelatedModel(models.TransientModel):
    _name = 'mo_accounting_tools.update_acc_acc_in_am_line_wizard_line'
    _description = 'Your Related Model Description'

    # name = fields.Char('Name')
    am_line_id = fields.Many2one(string='AM line',
                                 comodel_name='account.move.line',
                                 )
    am_line_id_id = fields.Integer(string='move_id',
                                   related='am_line_id.id',
                                   )

    am_line_account_id = fields.Many2one(string='account_id',
                                         related='am_line_id.account_id',
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
                                comodel_name='mo_accounting_tools.update_acc_acc_in_am_line_wizard',
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


class UpdateAccAccInAmLineWizard(models.TransientModel):
    _name = 'mo_accounting_tools.update_acc_acc_in_am_line_wizard'
    _inherit = 'mo_accounting_tools.wizard_mixin'
    _description = 'update_acc_acc_in_am_line_wizard'

    version_id = fields.Char(string='Version',
                             size=4,
                             default='v1.9',
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
                                         [('code', '=', 281100)]))

    journal_id = fields.Many2one(string='Account journal',
                                 comodel_name='account.journal',
                                 default=lambda self: self.env['account.journal'].search(
                                     [('name', '=', "Оцінка запасу")]))

    #                              default=lambda self: self.env['account.journal'].browse(8)
    #                              )

    date_start = fields.Date(string='Date from',
                             default=lambda self: datetime.now().replace(day=1, hour=0, minute=0, second=0))

    date_finish = fields.Date(string='Date to',
                              default=fields.Date.today())

    limit_rec = fields.Integer(string='limit',
                               default=200,
                               )

    line_ids = fields.One2many(string='Lines',
                               comodel_name='mo_accounting_tools.update_acc_acc_in_am_line_wizard_line',
                               inverse_name='wizard_id',
                               )

    # logs = fields.Text(string='Text',
    #                    default="",
    #                    help='This is Text field',
    #                    )

    # =======================================================
    def cron_update_am_line_by_analytic_account(self, str_cron_start_time_on, str_cron_start_time_off, date_start,
                                                date_finish, account_id_code, account_id_new_code, journal_id_name,
                                                limit_rec):

        # ограничение по времени старта Крона
        if not self.mixin_check_start_time(str_cron_start_time_on, str_cron_start_time_off):
            return

        if not date_start:
            date_start = datetime(2023, 1, 1, 0, 0, 0)

        account_id, account_id_id = self.mixin_search_account_id_by_code(account_id_code)
        account_id_new, account_id_new_id = self.mixin_search_account_id_by_code(account_id_new_code)
        journal_id, journal_id_id = self.mixin_search_journal_id_by_name(journal_id_name)

        list_am_line = self._get_am_line_by_account_account(date_start, date_finish, account_id_id, account_id_new_id,
                                                            journal_id_id, limit_rec)

        self._update_am_line_by_account_account(account_id_new, list_am_line)

    # =======================================================
    def button_update_am_line_by_account_account(self):
        self._update_am_line_by_account_account(self.account_id_new, self.line_ids)

        # открыть форму wizard
        return {
            'context': self.env.context,
            # 'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mo_accounting_tools.update_acc_acc_in_am_line_wizard',
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

        # =======================================================

    def button_get_am_line_by_account_account(self):
        self._get_am_line_by_account_account(self.date_start, self.date_finish, self.account_id, self.account_id_new,
                                             self.journal_id, self.limit_rec, False)

        # открыть форму wizard
        return {
            'context': self.env.context,
            # 'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mo_accounting_tools.update_acc_acc_in_am_line_wizard',
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

    # =======================================================
    def _get_am_line_by_account_account(self, date_start, date_finish, account_id_id, account_id_new_id, journal_id_id,
                                        limit_rec, is_return_only_list):

        if not account_id_id or not account_id_new_id:
            return

        domen_list = [('account_id', '=', account_id_id),
                      ('journal_id', '=', journal_id_id),
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

        total_ind = len(account_move_line_records)
        ind = 0
        for record_am_line in account_move_line_records:
            ind += 1

            new_line = {
                'wizard_id': self.id,
                'am_line_id': record_am_line.id,
                'move_id': record_am_line.move_id.id,
            }

            new_lines_list.append(new_line)
        if is_return_only_list:
            return new_lines_list

        self.line_ids.create(new_lines_list)

    # =======================================================
    def _update_am_line_by_account_account(self, account_id_new, line_ids):

        # self.logs = ""
        total_ind = len(line_ids)
        ind = 0
        for line in line_ids:
            record_am_line = line.am_line_id
            ind += 1

            str_log = f"Обр. {ind} из {total_ind} {record_am_line}"
            _logger.info(str_log)

            vals = {'account_id': account_id_new.id}

            # заполним поле - какой был старый бух счет
            if not record_am_line.temp_account_id:
                vals['temp_account_id'] = record_am_line.account_id.id

            if len(vals) > 0:
                record_am_line.with_context(
                    skip_invoice_sync=True,
                    skip_invoice_line_sync=True,
                    skip_account_move_synchronization=True,
                    check_move_validity=False,
                ).write(vals)
