# Copyright © 2019 Oleksandr Komarov (https://modool.pro) <info@modool.pro>
# See LICENSE file for licensing details.

from odoo import models, fields


class SaveConfToFile(models.TransientModel):
    _name = 'o1c.save.conf'
    _description = 'Save Configuration'

    file_name = fields.Char('File name', readonly=True)
    xml_file = fields.Binary('Conf as XML', readonly=True)
    description = fields.Char('Info', readonly=True)
