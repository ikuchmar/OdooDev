from odoo import fields, models, api
from odoo.exceptions import UserError

class BtUom(models.Model):
    _name = 'bt.uom'
    _description = 'Bt Trade Uom'

    name = fields.Char(string='Uom',
                       required=True)

    def _check_links(self):
        used_in_list = []
        for record in self.env['ir.model.fields'].search([('relation', '=', self._name)]):
            filled = self.env[record.model].search([(record.name, '!=', False)])
            if filled:
                used_in_list.append(filled)
        return used_in_list

    def unlink(self):
        for record in self:
            filled_list = record._check_links()
            if filled_list:
                raise UserError('Nope!')
            else:
                return super(BtUom, self).unlink()
