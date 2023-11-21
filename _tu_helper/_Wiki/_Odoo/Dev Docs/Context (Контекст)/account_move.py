# -*- coding: utf-8 -*-

import logging
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ===================================================
    def write(self, vals):
        if self._context.get('skip_check_am_number_month_year') == True:
            return super(AccountMove, self).write(vals)

        # когда state меняется на draft или cancel - не нужно блокировать (и проверять)
        if vals.get('state', False) in ('draft', 'cancel'):
            # добавляем контекст - если опять попадем во врайт с vals уже без state - чтобы все таки не проверять
            return super(AccountMove, self.with_context(
                skip_check_am_number_month_year=True,
            )).write(vals)

        for record in self:
            record._check_am_number_month_year()

        return super(AccountMove, self).write(vals)

    # ===================================================
    def _set_next_sequence(self):
        super(AccountMove, self)._set_next_sequence()
        # наверное при создании номера - не нужно проверять - только при записи..?
        # self._check_am_number_month_year()

    # ===================================================
    def _check_am_number_month_year(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        block_incorrect_am_number = get_param('mo_accounting.block_incorrect_am_number', 'False')

        for am in self:
            if not am.date or not am.name:
                continue
            last_sequence = am.name
            format, format_values = am._get_sequence_format_param(last_sequence)

            if not format_values.get('year') or not format_values.get('month'):
                _logger.warning('cant parse Acc.Move[%s] number: %s', am, am.name)
                continue

            if str(format_values['month']) != str(am.date.month) \
                    or str(format_values['year']) != str(am.date.year):
                user = am.env.user.sudo()
                _logger.error(
                    'ERRRRRROOOOOR!!!!! Acc.Move[%s] number: %s '
                    'but AM.date is: %s!! User[%s] %s', am, am.name, am.date, am.env.uid, user.name)

                if block_incorrect_am_number == 'True':
                    raise UserError(
                        'Рік %s та-або Місяць %s у Номері %s '
                        'не співпадають з датою %s AM %s' % (format_values['year'], format_values['month'],
                                                             am.name, am.date, am.id))
