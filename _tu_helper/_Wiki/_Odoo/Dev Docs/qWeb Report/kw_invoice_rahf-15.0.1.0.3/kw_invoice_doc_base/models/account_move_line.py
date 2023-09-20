import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    kw_is_added_to_doc = fields.Boolean(
        string='Is a configurable product',
        compute='_compute_kw_is_added_to_doc', )

    def _compute_kw_is_added_to_doc(self):
        for obj in self:
            obj.kw_is_added_to_doc = \
                obj.product_id.product_tmpl_id.kw_is_added_to_doc
