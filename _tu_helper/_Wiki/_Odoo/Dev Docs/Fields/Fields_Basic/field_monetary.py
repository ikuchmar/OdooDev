# from odoo import fields, models
#
#
# class BasicFields(models.Model):
#     _inherit = 'tu_helper.field_basic'
#
#     expected_revenue = fields.Integer('Expected Revenue',
#                                        currency_field='company_currency', tracking=True)
#
#     prorated_revenue = fields.Integer('Prorated Revenues',
#                                        currency_field='company_currency', store=True,
#                                        compute="_compute_prorated_revenue")
#
#     recurring_revenue = fields.Integer('Recurring Revenues',
#                                         currency_field='company_currency',
#                                         groups="crm.group_use_recurring_revenues", tracking=True)

# --------------------------------------------------------------------------------------
# Monetary - Це поле з плаваючою комою, що має зв’язок з валютою, параметр
# currency_field - назва Many2one поля, що містить валюту
# --------------------------------------------------------------------------------------
