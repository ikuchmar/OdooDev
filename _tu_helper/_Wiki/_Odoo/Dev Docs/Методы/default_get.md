default_get
==========================================================
Повертає значення за замовчуванням для переданого списку полів. Обчислені у наступному пріоритеті:
1.	Контекст
2.	Значення в ir.default (визначені користувачем)
3.	Значення за замовчуванням, що визначені в полях моделі
4.	Значення для поля з батьківської моделі

    @api.model
    def default_get(self, fields):
       vals = super(AccountBankStmtCashWizard, self).default_get(fields)
       balance = self.env.context.get('balance')
       statement_id = self.env.context.get('statement_id')
       if 'start_bank_stmt_ids' in fields and not vals.get('start_bank_stmt_ids') \
    and statement_id and balance == 'start':
           vals['start_bank_stmt_ids'] = [(6, 0, [statement_id])]
       if 'end_bank_stmt_ids' in fields and not vals.get('end_bank_stmt_ids') \
    and statement_id and balance == 'close':
           vals['end_bank_stmt_ids'] = [(6, 0, [statement_id])]
    
       return vals

Перевизначення використовується, наприклад, коли значення за замовчуванням мають залежності один від одного.

     def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res['patient_ids'] = [(6, 0, self._context_get("active_ids"))]
        return res
    
     def action_set(self):
        self.ensure_one()
        patient_for_set = self.env["patient"].browse(self._context.get("active_ids"))
        for patient in patient_for_set:
            patient.write({"personal_doctor_id": self.doctor_id.id})

