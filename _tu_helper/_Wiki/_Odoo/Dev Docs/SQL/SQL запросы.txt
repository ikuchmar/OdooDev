Выборка всех записей из таблицы "res_partner":
lua
Copy code
self.env.cr.execute("SELECT * FROM res_partner")
result = self.env.cr.fetchall()
Выборка всех записей из таблицы "res_partner" с условием, что поле "country_id" равно "us":
python
Copy code
self.env.cr.execute("SELECT * FROM res_partner WHERE country_id = %s", (self.env.ref('base.us').id,))
result = self.env.cr.fetchall()
Изменение поля "name" для записи с определенным идентификатором в таблице "res_partner":
lua
Copy code
self.env.cr.execute("UPDATE res_partner SET name = %s WHERE id = %s", ('New Name', 1))
self.env.cr.commit()
Создание новой записи в таблице "res_partner":
lua
Copy code
self.env.cr.execute("INSERT INTO res_partner (name) VALUES (%s)", ('New Partner',))
self.env.cr.commit()
Удаление записи с определенным идентификатором из таблицы "res_partner":
lua
Copy code
self.env.cr.execute("DELETE FROM res_partner WHERE id = %s", (1,))
self.env.cr.commit()
Важно помнить, что прямые SQL-запросы могут быть опасными и приводить к потере данных или нарушению целостности базы данных. Поэтому необходимо использовать их с осторожностью и проверять все данные, передаваемые в запросах.