from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _name = 'product.template'

    kw_is_added_to_doc = fields.Boolean(
        string="Is product added to invoices", default=True,
        help="If checked, the product will be added to the invoice.")
