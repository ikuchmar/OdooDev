from odoo import models, fields
import base64
import json


class ImportTranslation(models.TransientModel):
    _name = 'import.translation'
    _description = 'Import translation from JSON'

    json_file = fields.Binary(string='Json file')
    json_name = fields.Char(string='Json name')
    field_type = fields.Selection([
        ('simple', 'Simple'),
        ('translated', 'Translated'),
    ], string='Field type')

    def import_data(self):
        translation_data = json.loads(base64.decodebytes(self.json_file).decode('utf8'))
        if self.field_type == 'translated':
            for model, ids in translation_data.items():
                for id, fields in ids.items():
                    for field, value in fields.items():
                        self.env.cr.execute(f"""UPDATE {model.replace('.', '_')} SET {field} = '{json.dumps(value, ensure_ascii=False).replace("'", "''")}' WHERE id = {id}""")

        else:
            for model, ids in translation_data.items():
                for id, fields in ids.items():
                    for field, value in fields.items():
                        self.env[model].search([('id', '=', int(id))]).write({
                            field: value['uk_UA'] if value.get('uk_UA') else value.get('en_US')
                        })
