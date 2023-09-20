from odoo import fields, models, api


class ProcurementGroupPurchase(models.Model):
    _inherit = 'procurement.group'

    @api.model
    # def run_scheduler_from_purchase(self, id):
    def run_scheduler_from_purchase(self, id=None):
        self.run_scheduler(True)
