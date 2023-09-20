from odoo import fields, models


class Many2manyFields(models.Model):
    _name = 'field.many2many'

    season_allowed_product_ids = fields.Many2many(string="Season allowed products",
                                                  comodel_name="product.product",
                                                  relation="season_product_rel",
                                                  column1="sale_id",
                                                  column2="product_id",
                                                  help='Description of the Many2many field',
                                                  )


    # comodel_name - имя модели, с которой связано поле типа many2many.
    # relation - название таблицы связи между текущей моделью и моделью comodel_name.
    # column1 - название столбца, который связывает текущую модель с таблицей связи.
    # column2 - название столбца, который связывает модель comodel_name с таблицей связи.
    # string - название поля, которое будет отображаться на форме в интерфейсе пользователя.
    # help - описание поля, которое будет отображаться на форме в интерфейсе пользователя в виде всплывающей подсказки.

    # --------------------------------------------------------------------------------------
    # Many2many
    # --------------------------------------------------------------------------------------
    # Це поле використовує реалізацію зв’язаку “Багато до багатьох” через проміжну таблицю в БД.
    # Так на цю таблицю можна прив’язати модель, додати додаткові поля. Але краще використати модель та комбінацію полів Many2one та One2many.
    #
    # comodel_name - обов’язковий параметр, що містить назву моделі, на яку посилається поле
    # relation - назва таблиці в БД
    # column1 - назва поля (що створюється - в таблиці Many2many), що посилається на поточну модель
    # column2 - назва поля, що посилається на пов’язано модель
    #
    # Важливо! Якщо потрібно зробити двосторонній зв’язок, між двома моделями, поле relation треба заповнити в обох полях і вказати однакову назву.
    # Reference
    # Це поле не створює відносин засобами СУБД, є строковим і зберігає значення у вигляді  "res_model,res_id". Використовує віджет reference, який дозволяє вибрати модель і вже в моделі запис.
    # resource_ref = fields.Reference(
    #    string="Resource Ref', selection='_selection_target_model',
    #    compute='_compute_resource_ref', readonly=True)
    # selection - параметр, що обмежує список моделей, що можуть бути вибрані в цьому полі. Формат аналогічний такого ж парамету у полі Selection.
    #
    # Many2oneReference
    # Це поле також не створює зв’язків засобами СУБД. Є цілочисельним і зберігає id запису.
    # res_id = fields.Many2oneReference('Resource ID', model_field='res_model',
    #                  readonly=True, help="The record id this is attached to.")
    # <field name="reference" widget="reference" string="Record"/>
    # model_field - обов’язковий параметр, що містить назву моделі, на яку посилається поле
    # вивід колонок в поле  x2m (в представлении)
    # <field name="aaa">
    # <tree>
    #   <field name="name"/>
    #   <field name="another_field"/>
    # </tree>
    # </field>
    # Виджети м2м
    # https://odoo-ua.com/blog/programuvannia-2/vidzheti-dlia-poliv-tipu-many2one-23
    # м2м - в Визарде (второе поле на визард)
    # class HrHospitalSetDoctorForPatientsWizard(models.TransientModel):
    #   _name = 'cgu_hospital.set.doctor.wizard'
    #   _description = "Wizard to set_doctor_for_patients"
    #
    #   patient_ids = fields.Many2many(
    #     string="patients',
    #     comodel_name='cgu_hospital.patient',
    #     relation = 'set_doctor_wizard_rel'
    #     #column2='patient_id'
    #     )
