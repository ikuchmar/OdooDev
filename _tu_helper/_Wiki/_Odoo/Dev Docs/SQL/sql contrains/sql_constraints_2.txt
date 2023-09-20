==========================================
Ограничение на уникальность значения поля
==========================================

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'

    name = fields.Char('Name', required=True, index=True)
    code = fields.Char('Code', required=True, index=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code must be unique.'),
    ]
Это ограничение гарантирует уникальность значений поля code в таблице базы данных, на которую отображается модель my.model.

==========================================
Ограничение на значения поля, использующее функцию проверки
==========================================

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'

    name = fields.Char('Name', required=True)
    age = fields.Integer('Age', required=True)

    _sql_constraints = [
        ('age_check', 'CHECK (age >= 18)', 'Age should be greater than or equal to 18.'),
    ]
Это ограничение гарантирует, что значения поля age будут больше или равны 18 в таблице базы данных, на которую отображается модель my.model.

==========================================
Ограничение на соответствие значения поля определенному шаблону
==========================================

arduino
Copy code
class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'

    name = fields.Char('Name', required=True)
    phone = fields.Char('Phone')

    _sql_constraints = [
        ('phone_check', 'CHECK (phone ~* \'^\\+\\d{1,3} \\d{3} \\d{3}-\\d{2}-\\d{2}$\')', 'Invalid phone format.'),
    ]
Это ограничение гарантирует, что значение поля phone будет соответствовать определенному регулярному выражению в таблице базы данных, на которую отображается модель my.model. В данном случае, регулярное выражение соответствует формату номера телефона вида "+XXX YYY ZZZ-ZZ-ZZ", где X - код страны, Y - код региона, Z - номер телефона.