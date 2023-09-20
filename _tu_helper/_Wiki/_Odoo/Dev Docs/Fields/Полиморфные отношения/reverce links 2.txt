Для этого можно использовать механизм обратных ссылок (reverse links) в модели Odoo.

Допустим, у нас есть две модели: Model1 и Model2, и мы хотим, чтобы при создании и изменении Model1 в Model2 создавалась или обновлялась запись с соответствующими данными.

Сначала необходимо создать поле обратной ссылки в модели Model2 на модель Model1:
python
Copy code
class Model2(models.Model):
    _name = 'model2'
    name = fields.Char(string='Name')
    model1_id = fields.Many2one('model1', string='Model 1')
Затем добавим поле обратной ссылки в модель Model1:
python
Copy code
class Model1(models.Model):
    _name = 'model1'
    name = fields.Char(string='Name')
    model2_ids = fields.One2many('model2', 'model1_id', string='Model 2')
Создаем метод create_or_update_model2() в модели Model1, который будет вызываться при создании или изменении записи в Model1 и создавать или обновлять запись в Model2:
python
Copy code
class Model1(models.Model):
    _name = 'model1'
    name = fields.Char(string='Name')
    model2_ids = fields.One2many('model2', 'model1_id', string='Model 2')

    def create_or_update_model2(self):
        for record in self:
            # Проверяем, есть ли запись в Model2
            model2 = self.env['model2'].search([('model1_id', '=', record.id)])
            if model2:
                # Если запись уже есть, обновляем ее
                model2.write({'name': record.name})
            else:
                # Если записи нет, создаем ее
                self.env['model2'].create({'name': record.name, 'model1_id': record.id})
Наконец, переопределяем методы create() и write() в модели Model1, чтобы вызывать create_or_update_model2() после создания или изменения записи:
python
Copy code
class Model1(models.Model):
    _name = 'model1'
    name = fields.Char(string='Name')
    model2_ids = fields.One2many('model2', 'model1_id', string='Model 2')

    def create_or_update_model2(self):
        for record in self:
            # Проверяем, есть ли запись в Model2
            model2 = self.env['model2'].search([('model1_id', '=', record.id)])
            if model2:
                # Если запись уже есть, обновляем ее
                model2.write({'name': record.name})
            else:
                # Если записи нет, создаем ее
                self.env['model2'].create({'name': record.name, 'model1_id': record.id})

    @api.model
    def create(self, vals):
        record = super(Model1, self).create(vals)
        record.create_or_update_model2()
        return record

    def write(self, vals):
        res = super(Model1, self).write(vals)
        self.create_or_update_model2()
        return res
Теперь при создании или