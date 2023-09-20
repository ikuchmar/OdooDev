как организовать чтобы при создании и изменении первой модели - всегда во второй  моделе существовала запись, которая связана с первой (в первое есть поле m2o), и существовала третья модель с линиями связанной со второй моделью  (во второй моделе есть поле o2m на третью модель) и первая модель управляла содержанием третьей модели

Для организации такой связи между моделями можно использовать следующую схему:

В первой модели (ModelA) создаем поле типа Many2one, связывающее ее с второй моделью (ModelB). Для этого в файле модели ModelA нужно добавить следующий код:
python
Copy code
class ModelA(models.Model):
    _name = 'model.a'

    model_b_id = fields.Many2one('model.b', string='Model B')
Во второй модели (ModelB) создаем поле типа One2many, связывающее ее с третьей моделью (ModelC). Также в этой модели можно определить метод для автоматического создания записи в ModelC при создании или изменении записи в ModelB. Для этого в файле модели ModelB нужно добавить следующий код:
python
Copy code
class ModelB(models.Model):
    _name = 'model.b'

    model_c_ids = fields.One2many('model.c', 'model_b_id', string='Model C')

    @api.model
    def create(self, vals):
        record = super(ModelB, self).create(vals)
        self.env['model.c'].create({'model_b_id': record.id})
        return record

    def write(self, vals):
        result = super(ModelB, self).write(vals)
        if 'model_c_ids' not in vals:
            for record in self:
                if not record.model_c_ids:
                    self.env['model.c'].create({'model_b_id': record.id})
        return result
В третьей модели (ModelC) создаем поля, необходимые для хранения данных. Также в этой модели можно определить метод для автоматического обновления данных при изменении записей в ModelA или ModelB. Для этого в файле модели ModelC нужно добавить следующий код:
python
Copy code
class ModelC(models.Model):
    _name = 'model.c'

    model_b_id = fields.Many2one('model.b', string='Model B')
    field1 = fields.Char(string='Field 1')
    field2 = fields.Char(string='Field 2')
    ...

    @api.model
    def create(self, vals):
        record = super(ModelC, self).create(vals)
        if record.model_b_id and not record.model_b_id.model_a_id:
            record.model_b_id.model_a_id = record.model_b_id.model_a_id.id
        return record

    def write(self, vals):
        result = super(ModelC, self).write(vals)
        if 'model_b_id' in vals:
            for record in self:
                if record.model_b_id and not record.model_b_id.model_a_id:
                    record.model_b_id.model_a_id = record.model_b_id.model_a_id.id
        return result
Теперь при создании или изменении записей в ModelA автоматически создается или обновляется связанная запись в ModelC, при создании или изменении записей в ModelB автоматически создается или обновляется связанная запись в ModelC, а при создании записей в ModelB автоматически создается связанная запись в ModelC.