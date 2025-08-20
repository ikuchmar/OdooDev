from odoo import models, fields

class SampleThing(models.Model):
    _name = "sample.thing"
    name = fields.Char(string="Name", required=True)
