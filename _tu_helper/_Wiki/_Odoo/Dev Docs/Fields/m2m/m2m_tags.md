===========================================
 model_with_m2m.py
===========================================
class model_with_m2m(models.Model):
    _name = 'cgu_test_filelds.model_with_m2m'
    _description = 'cgu_test_filelds.model_with_m2m'

    name = fields.Char()

    tags_ids = fields.Many2many(
        string='Tags', comodel_name='cgu_test_filelds.tags')

===========================================
tags.py
===========================================
class Tags(models.Model):

    _name = "cgu_test_filelds.tags"
    _description = "cgu_test_filelds.tags"

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

========================================================
Представление widget="many2many_tags"
========================================================
<field name="partner_ids" widget="many2many_tags"/>

<field name="tags_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>

<tree string="">
    <field name="name"/>
    <field name="tags_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
</tree>


