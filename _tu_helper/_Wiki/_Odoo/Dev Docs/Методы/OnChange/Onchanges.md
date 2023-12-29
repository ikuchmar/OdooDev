
Onchanges
==================================
позволяет клиентскому интерфейсу обновлять форму без сохранения чего-либо в базе данных всякий раз, когда пользователь заполняет значение поля


    from odoo import api, fields, models
    
    class TestOnchange(models.Model):
        _name = "test.onchange"
    
        name = fields.Char(string="Name")
        description = fields.Char(string="Description")
        partner_id = fields.Many2one("res.partner", string="Partner")
    
        @api.onchange("partner_id")
        def _onchange_partner_id(self):
            self.name = "Document for %s" % (self.partner_id.name)
            self.description = "Default description for %s" % (self.partner_id.name)

Декоратор для виклику методів при зміні значення полів на формі.
Так це фронтенд метод.
Працює лише на формах.
Працює лише за умови наявності поля на формі.
Працює лише з полями моделі.
Не можна використовувати методи запису в БД create(),  write(), unlink().
Поля типу one2many чи many2many не можуть змінювати себе.
Можна викликати повідомлення (виглядають як діалог помилки)

@api.onchange('posted_before', 'state', 'journal_id', 'date')
def _onchange_journal_date(self):
   if not self.move_id:
       self.name = False

@api.onchange('journal_id')
def _onchange_journal(self):
   self.move_id._onchange_journal()

@api.onchange('tax_exigibility')
def _onchange_tax_exigibility(self):
   res = {}
   tax = self.env['account.tax'].search([
       ('company_id', '=', self.env.company.id),
       ('tax_exigibility', '=', 'on_payment')
   ], limit=1)
   if not self.tax_exigibility and tax:
       self.tax_exigibility = True
       res['warning'] = {
           'title': _('Error!'),
           'message': _('You cannot disable this setting.') }
   return res

- в нем нельзя использовать create
Нужно делать через поле о2м

history_doctor_ids = fields.One2many('hr_hospital.history.doctor',
                                        inverse_name='patient_id')

@api.onchange('doctor_id')
def onchange_doctor_id(self):
    for rec in self:
        lines = []
        vals = {
            'date': date.today(),
            'patient_id': rec.id,
            'doctor_id': rec.doctor_id
        }
        lines.append((0, 0, vals))
        rec.history_doctor_ids = lines

==========================================================
@api.onchange
==========================================================
Декоратор для виклику методів при зміні значення полів на формі.
Так це фронтенд метод.
Працює лише на формах.
Працює лише за умови наявності поля на формі.
Працює лише з полями моделі.
Не можна використовувати методи запису в БД create(),  write(), unlink().
Поля типу one2many чи many2many не можуть змінювати себе.
Можна викликати повідомлення (виглядають як діалог помилки)

@api.onchange('posted_before', 'state', 'journal_id', 'date')
def _onchange_journal_date(self):
   if not self.move_id:
       self.name = False

@api.onchange('journal_id')
def _onchange_journal(self):
   self.move_id._onchange_journal()

@api.onchange('tax_exigibility')
def _onchange_tax_exigibility(self):
   res = {}
   tax = self.env['account.tax'].search([
       ('company_id', '=', self.env.company.id),
       ('tax_exigibility', '=', 'on_payment')
   ], limit=1)
   if not self.tax_exigibility and tax:
       self.tax_exigibility = True
       res['warning'] = {
           'title': _('Error!'),
           'message': _('You cannot disable this setting.') }
   return res

- в нем нельзя использовать create
Нужно делать через поле о2м

history_doctor_ids = fields.One2many('hr_hospital.history.doctor',
                                        inverse_name='patient_id')

@api.onchange('doctor_id')
def onchange_doctor_id(self):
    for rec in self:
        lines = []
        vals = {
            'date': date.today(),
            'patient_id': rec.id,
            'doctor_id': rec.doctor_id
        }
        lines.append((0, 0, vals))
        rec.history_doctor_ids = lines