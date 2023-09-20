В этом примере мы создаем виртуальное поле "partner_name", которое зависит от поля "partner_id".
Мы используем декоратор @api.depends, чтобы сообщить Odoo, что поле "partner_name" должно быть обновлено,
когда изменяется поле "partner_id". В функции _compute_partner_name мы проходимся по всем записям и устанавливаем
значение поля "partner_name" равным значению поля "name" у соответствующего партнера.

Обратите внимание, что мы используем параметр store=True, чтобы сохранить значение виртуального поля в базе данных.
Это обеспечит более быстрый доступ к этому полю при чтении записей. Если параметр store не установлен в True,
то виртуальное поле не будет сохранено в базе данных, а его значение будет вычисляться каждый раз при чтении записи,
что может снижать производительность.

общий вид
=====================================================

    class MyModel(models.Model):
        _name = 'my.model'
    
        partner_name = fields.Char(string="Partner Name", compute="_compute_partner_name", store=True)
    
        @api.depends('partner_id')
        def _compute_partner_name(self):
            for record in self:
                record.partner_name = record.partner_id.name


чтобы в процедуру compute - передать параметр
=====================================================

    amount_total_float = fields.Float(compute=lambda self: self._compute_amount_float("total"), index=True)
    amount_untaxed_float = fields.Float(compute=lambda self: self._compute_amount_float("untaxed"), index=True)

    # ==========================================
    @api.depends('amount_total', 'amount_untaxed')
    def _compute_amount_float(self, val):
        for record in self:
            if val == "total":
                record.amount_total_float = record.amount_total
            elif val == 'untaxed':
                record.amount_untaxed_float = record.amount_untaxed

@api.depends
=====================================================

Вказує зміни яких полів викликають переобчислення compute метода. 
Метод не буде працювати для інших полів, а також при зміні значень полів на бекенді.

    @api.depends('line_ids', 'line_ids.is_landed_costs_line')
    def _compute_landed_costs_visible(self):
       for account_move in self:
           if account_move.landed_costs_ids:
               account_move.landed_costs_visible = False
           else:
               account_move.landed_costs_visible = any(line.is_landed_costs_line for line in account_move.line_ids)

==========================================================
Метод вычисления поля: @api.depends
==========================================================
    @api.depends('field1', 'field2')
    def _compute_my_field(self):
        for record in self:
            record.my_field = record.field1 + record.field2
В этом примере мы создаем метод _compute_my_field в модели MyModel. 
Этот метод вычисляет значение поля my_field на основе значений полей field1 и field2. 
Метод использует декоратор @api.depends для указания, какие поля зависят от вычисляемого поля. 
Когда значение одного из этих полей изменяется, метод будет вызываться для пересчета значения поля my_field.

==========================================================
@api.depends
==========================================================
Вказує зміни яких полів викликають переобчислення compute метода.
Метод не буде працювати для інших полів, а також при зміні значень полів на бекенді.

@api.depends('line_ids', 'line_ids.is_landed_costs_line')
def _compute_landed_costs_visible(self):
   for account_move in self:
       if account_move.landed_costs_ids:
           account_move.landed_costs_visible = False
       else:
           account_move.landed_costs_visible = any(
line.is_landed_costs_line for line in account_move.line_ids)


==========================================================
депенс через точку - как релатид поля  @api.depends('move_id.journal_id.type')
==========================================================

journal_type = fields.Char(compute='_compute_journal_type')

@api.depends('move_id.journal_id.type')
def _compute_journal_type(self):
    for rec in self:
        rec.journal_type = str(rec.move_id.journal_id.type)