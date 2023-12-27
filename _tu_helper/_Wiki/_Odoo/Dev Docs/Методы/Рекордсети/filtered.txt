===================================================
filtered та filtered_domain
===================================================

Методи filtered та filtered_domain дозволяють створити з вказаного рекордесету, рекордсет з записами, що відповідають вказаним умовам.
Для filtered можна вказати поле або функцію фільтрації, для filtered_domain домен.

records.filtered(lambda r: r.company_id == user.company_id)
records.filtered("partner_id.is_company")
events = self.filtered_domain([('alarm_ids', '!=', False)])
