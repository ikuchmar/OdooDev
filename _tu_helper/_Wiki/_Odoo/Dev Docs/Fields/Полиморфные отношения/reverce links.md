Для реализации автоматического создания и обновления записей во второй модели при создании и изменении записей в первой модели можно использовать функциональное поле и метод write() с атрибутом create=True.

Создайте функциональное поле в первой модели, которое будет связано с второй моделью. Например, если первая модель называется ModelA, а вторая - ModelB, то функциональное поле в ModelA можно создать следующим образом:
python
Copy code
class ModelA(models.Model):
    _name = 'model.a'

    model_b_ids = fields.One2many('model.b', 'model_a_id', compute='_compute_model_b_ids', store=True)

    @api.depends('name')
    def _compute_model_b_ids(self):
        for rec in self:
            model_b = self.env['model.b'].search([('name', '=', rec.name)], limit=1)
            if model_b:
                rec.model_b_ids = [(6, 0, model_b.ids)]
            else:
                rec.model_b_ids = [(5,)]
В данном примере мы создали функциональное поле model_b_ids, которое вычисляется при изменении поля name и связано с моделью ModelB через поле model_a_id.

В методе write() первой модели добавьте обновление или создание записи второй модели с помощью атрибута create=True. Например:
lua
Copy code
class ModelA(models.Model):
    _name = 'model.a'

    def write(self, vals):
        res = super(ModelA, self).write(vals)
        if 'name' in vals:
            for rec in self:
                model_b = self.env['model.b'].search([('name', '=', rec.name)], limit=1)
                if model_b:
                    model_b.write({'value': rec.value})
                else:
                    self.env['model.b'].create({'name': rec.name, 'value': rec.value, 'model_a_id': rec.id})
        return res
В данном примере мы добавили обновление или создание записи второй модели при изменении поля name первой модели. Если запись второй модели существует, то мы обновляем ее значение value, иначе создаем новую запись с помощью метода create(). При создании новой записи мы также передаем значение поля model_a_id, чтобы связать ее с текущей записью первой модели.

Таким образом, при создании или изменении записи в первой модели, запись второй модели будет автоматически создаваться или обновляться в зависимости от наличия связанных данных.





Regenerate response
