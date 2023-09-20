import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    legal_name = fields.Char(
        string='Legal full name', translate=True, )
    legal_short_name = fields.Char(
        translate=True, help='The short legal name of the partner', )
    tax_ident_number = fields.Char(
        string='Individual tax identification number', size=13, )
    payer_certificate_number = fields.Char(
        string='VAT certificate number', size=13, )
    enterprise_code = fields.Char(
        size=13, )
    chief_reason = fields.Text(
        store=True, )
    chief = fields.Many2one(
        comodel_name='res.partner', string='Director', )
    chief_accountant = fields.Many2one(
        comodel_name='res.partner', )
    responsible_officer = fields.Many2one(
        comodel_name='res.partner', )
    legal_address = fields.Many2one(
        comodel_name='res.partner', )
    postal_address = fields.Many2one(
        comodel_name='res.partner', )
    kw_taxation_scheme_id = fields.Many2one(
        string='Taxation scheme', comodel_name='kw.taxation.scheme')


class TaxStatus(models.Model):
    _name = "kw.taxation.scheme"
    _description = 'Tax Status'

    name = fields.Char()
