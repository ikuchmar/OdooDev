from odoo import api, fields, tools, models, _
from odoo.exceptions import UserError, ValidationError
class UnitsOfMeasure(models.Model):
    _name = 'is.trade.uom'
    _description = 'Units of Measure'

    name = fields.Char('Units of Measure')
