import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError as err:
    _logger.debug(err)


class AccountMove(models.Model):
    _inherit = 'account.move'

    kw_responsible_person = fields.Many2one(
        comodel_name='res.partner', string='Responsible person',
        domain="[('parent_id','=',partner_id)]")
    kw_city_of_assembly = fields.Char(
        string='City of assembly',
        default=lambda self: self.env.user.company_id.city)
    kw_amount_ukr_text = fields.Char(
        compute='_compute_kw_amount_ukr_text', )
    kw_amount_untaxed_ukr_text = fields.Char(
        compute='_compute_kw_amount_untaxed_ukr_text', )
    kw_taxed_ukr_text = fields.Char(
        compute='_compute_kw_taxed_ukr_text', )
    kw_currency_name = fields.Char(
        compute='_compute_kw_currency_name', )
    kw_currency_cent_name = fields.Char(
        compute='_compute_kw_currency_name', )
    kw_partner_invoice_id = fields.Many2one(
        comodel_name='res.partner', compute='_compute_kw_partner_invoice_id', )
    kw_contract = fields.Char(string='Agreement')

    def _compute_kw_partner_invoice_id(self):
        for obj in self:
            if hasattr(obj, 'partner_invoice_id') and obj.partner_invoice_id:
                obj.kw_partner_invoice_id = obj.partner_invoice_id.id
            else:
                obj.kw_partner_invoice_id = False

    def _compute_kw_amount_ukr_text(self):
        for obj in self:
            obj.kw_amount_ukr_text = '{} {} {:0>2} {}'.format(
                num2words(int(obj.amount_total), lang='uk'),
                self.kw_currency_name,
                round(100 * (obj.amount_total - int(obj.amount_total))),
                self.kw_currency_cent_name,
            ).capitalize()

    def _compute_kw_taxed_ukr_text(self):
        for obj in self:
            obj.kw_taxed_ukr_text = '{} {} {:0>2} {}'.format(
                num2words(int(obj.amount_tax), lang='uk'),
                self.kw_currency_name,
                round(100 * (obj.amount_tax - int(obj.amount_tax))),
                self.kw_currency_cent_name,
            ).capitalize()

    def _compute_kw_amount_untaxed_ukr_text(self):
        for obj in self:
            obj.kw_amount_untaxed_ukr_text = '{} {} {:0>2} {}'.format(
                num2words(int(obj.amount_untaxed), lang='uk'),
                self.kw_currency_name,
                round(100 * (obj.amount_untaxed - int(obj.amount_untaxed))),
                self.kw_currency_cent_name,
            ).capitalize()

    def _compute_kw_currency_name(self):
        for obj in self:
            if obj.currency_id.currency_unit_label == 'Euros':
                self.kw_currency_name = 'EUR'
                self.kw_currency_cent_name = 'cent'
            elif obj.currency_id.currency_unit_label == 'Dollars':
                self.kw_currency_name = 'USD'
                self.kw_currency_cent_name = 'cent'
            elif obj.currency_id.currency_unit_label == 'Hryvnia':
                self.kw_currency_name = 'грн.'
                self.kw_currency_cent_name = 'коп.'
            else:
                self.kw_currency_name = obj.currency_id.currency_unit_label
                self.kw_currency_cent_name = \
                    obj.currency_id.currency_subunit_label
