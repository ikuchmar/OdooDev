from odoo import api, fields, models
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    block_incorrect_am_number = fields.Boolean(string='Block incorrect AM number',
                                               config_parameter='mo_accounting.block_incorrect_am_number',
                                               default=True,
                                               )

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param
        set_param('mo_accounting.block_incorrect_am_number', str(self.block_incorrect_am_number))

    #     # set_param('mo_openapi_catalog.block_incorrect_am_number', str(self.block_incorrect_am_number))

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        get_param = self.env['ir.config_parameter'].sudo().get_param
        block_incorrect_am_number = literal_eval(get_param('mo_accounting.block_incorrect_am_number', 'True'))
        # block_incorrect_am_number = literal_eval(get_param('mo_openapi_catalog.block_incorrect_am_number', 'True'))
        res.update(block_incorrect_am_number=block_incorrect_am_number,
                   )

        return res
