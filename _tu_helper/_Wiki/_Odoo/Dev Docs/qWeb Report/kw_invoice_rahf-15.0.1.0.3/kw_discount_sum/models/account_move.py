import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError as err:
    _logger.debug(err)


class AccountMove(models.Model):
    _inherit = 'account.move'

    kw_discount_sum = fields.Float(
        string='Discount Sum', compute='_compute_kw_discount_sum',
        translate=True)
    kw_discount_sum_ukr_text = fields.Char(
        compute='_compute_discount_sum_ukr_text', )

    def _compute_discount_sum_ukr_text(self):
        for obj in self:
            obj.kw_discount_sum_ukr_text = '{} {} {:0>2} {}'.format(
                num2words(int(obj.kw_discount_sum), lang='uk'),
                self.kw_currency_name,
                round(100 * (obj.kw_discount_sum - int(obj.kw_discount_sum))),
                self.kw_currency_cent_name,
            ).capitalize()

    def _compute_kw_discount_sum(self):
        sum_discount = 0
        for order in self.invoice_line_ids:
            if order.discount > 0:
                discount_prod = (order.price_unit - (order.price_unit * (1 - (
                    order.discount) / 100.0))) * order.quantity
                sum_discount += discount_prod
        self.kw_discount_sum = sum_discount
