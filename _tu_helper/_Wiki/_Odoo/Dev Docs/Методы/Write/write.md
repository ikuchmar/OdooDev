write (метод recordset) *
=====================================
Змінює значення полів. Приймає словник поле-значення, оновлює всі вибрані записи.
--------------------------------------
check_records = env['mo.vchasnokasa.check'].search([], limit = 10)
check_records.write({'display_name': '15'})
======================================
vals - будет один для всех (словарь)
self - всегда итерируется
-----------------------------------------
    def write(self, vals):
        vals_new = vals.copy()
        for record in self:
            formatted_date = record.create_date.strftime("%Y-%m-%d %H:%M:%S") if record.create_date else ''
            check_type = record.check_type if record.check_type else ''
            fisn = record.fisn if record.fisn else ''

            vals_new['display_name'] = f"{check_type} {fisn} {formatted_date}"
            vals_new['check_type'] = self._task_type(record.task)

            # (MoVchasnokasaCheck имя класса)
            super(MoVchasnokasaCheck, record).write(vals_new)

        return True

-----------------------------------------
Змінює значення полів. Приймає словник поле-значення, оновлює всі вибрані записи.

    def write(self, vals):
       if 'stage_id' in vals and 'kanban_state' not in vals:
           # reset kanban state when changing stage
           vals['kanban_state'] = 'normal'
       res = super(EventEvent, self).write(vals)
       if vals.get('organizer_id'):
           self.message_subscribe([vals['organizer_id']])
       return res

-----------------------------------------
Перевизначається для доповнення параметрів або виконання дій з оновленими записами.

Вызов записи по созданным объектам

    def write(self, vals):
        if 'personal_doctor_id' not in vals:
            return super().write(vals)
        for obj in self:
            if  obj.paresonal_doctor_id.id != vals.get('personal_doctor_id'):
                    self.env['parsonal.doctor.history'].create({
                        'doctor_id': vals.get('personal_doctor_id'),
                        'patient_id': obj.id, 'appointment_date': date.today(), })
            super('Patient', obj).write(vals)
        return True

-----------------------------------------
Изменение значений при записи

    def write(self, vals):
        if 'persontal_doctor_id' not in vals:
            return super().write(vals)
        for obj.personal_doctor_id.id != vals.get('personal_doctor_id'):
            self.env['personal.doctor.hestory'].create({
                'doctor_id': vals.get('personal_doctor_id'),
                'patient_id': obj.id, 'appointment_date': date.today(), })
        val = vals.deepcopy()
        val['passport_number'] = '1111'
        super('Patient', obj).write(val)
        return True

