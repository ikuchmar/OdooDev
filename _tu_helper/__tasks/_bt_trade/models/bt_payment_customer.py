from odoo import models, fields, api


class BtPaymentCustomer(models.Model):
    _name = 'bt.payment.customer'
    _description = 'Payment customer'

    name = fields.Char(string='Name')

    partner_id = fields.Many2one(comodel_name='bt.partner',
                                 string='Partner')

    so_id = fields.Many2one(comodel_name='bt.sale.order',
                            string='Sale order')

    total_amount = fields.Float(string='Total amount')

    @api.model
    def create(self, vals_list):
        if not vals_list.get('name'):
            vals_list['name'] = self.env['ir.sequence'].next_by_code('bt.pc.sequence') or 'New'

        res = super(BtPaymentCustomer, self).create(vals_list)
        return res