# Copyright © 2019-2021 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

import logging

from odoo import models, fields
from odoo import api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class For1C(models.Model):
    _name = 'for.1c'
    _description = 'Export to 1C'
    _rec_name = 'res_choice'

    model = fields.Char('Model', required=True, index=True)
    res_id = fields.Integer('Res ID', required=True, index=True)
    updated = fields.Datetime('Updated', default=lambda self: fields.Datetime.now())
    conv_id = fields.Many2one('o1c.conv', ondelete='cascade', required=True, index=True)

    def get_models(self):
        return [(this_model, this_model) for this_model in self.env]

    res_choice = fields.Reference(
        get_models, string='Record', compute_sudo=True,
        store=False, ondelete='cascade', readonly=False, compute='_compute_res_choice')
    # kim 2023.04.оператор выполняет объединение двух множеств и присваивает результат обратно в левый операнд
    # res_date = fields.Date(string='Record Date', related='res_choice.date')
    res_date = fields.Date(string='Record Date', compute='_compute_res_date')
    # kim...

    _sql_constraints = [
        ('obj_uniq', 'unique(conv_id,model,res_id)', 'Object(conv_id,model, id) must be unique!'),
    ]

    @api.depends('res_choice')
    def _compute_res_date(self):
        for record in self:
            try:
                record.res_date = record.res_choice.date
            except:
                record.res_date = False

    def _compute_res_choice(self):
        # Warning: with search_read because _prefetch_field get other records and then raise AccessError
        data = self.sudo().search_read([('id', 'in', self.ids)], ['model', 'res_id', 'res_choice'])
        cs_data = {rec['id']: [rec['model'], rec['res_id'], rec['res_choice']] for rec in data}
        for rec in self:
            this_model = cs_data[rec.id][0]
            this_id = cs_data[rec.id][1]
            res_choice = False
            if this_model and this_id:
                try:
                    res_choice = self.env[this_model].sudo().browse(this_id)
                    res_choice.check_access_rights('read')
                    res_choice.check_access_rule('read')
                except AccessError:
                    _logger.debug('Record: %s Access denied to with missing Model: %s or Res ID: %s', rec.id,
                                  this_model, this_id)
                    res_choice = False
                except:
                    _logger.error('Record: %s with missing Model: %s or Res ID: %s', rec.id, this_model, this_id)
                    res_choice = False
            rec.res_choice = res_choice
