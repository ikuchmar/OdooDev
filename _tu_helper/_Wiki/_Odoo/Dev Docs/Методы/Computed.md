
https://www.odoo.com/documentation/15.0/developer/tutorials/getting_started/09_compute_onchange.html?highlight=compute

=====================================
Computed Fields

!!!! Вычислительные поля НЕ СОХРАНЯЮТСЯ в базе данных по умолчанию
(Другое решение — хранить поле с store=True атрибутом)

!!!! поле нужно заполнить обязательно (нельзя в методе оставить исходное поле без значения

=====================================

from odoo import api, fields, models

class TestComputed(models.Model):
    _name = "test.computed"

    total = fields.Float(compute="_compute_total")
    amount = fields.Float()

    @api.depends("amount")
    def _compute_total(self):
        for record in self:
            record.total = 2.0 * record.amount



------------------------------------
Inverse Function

Метод вычисления устанавливает поле, а обратный метод устанавливает зависимости поля.
Обратите внимание, что inverse метод вызывается при сохранении записи, а compute метод вызывается при каждом изменении ее зависимостей.
------------------------------------
  Для поддержки этого Odoo предоставляет возможность использовать inverseфункцию:

from odoo import api, fields, models

class TestComputed(models.Model):
    _name = "test.computed"

    total = fields.Float(compute="_compute_total", inverse="_inverse_total")
    amount = fields.Float()

    @api.depends("amount")
    def _compute_total(self):
        for record in self:
            record.total = 2.0 * record.amount

    def _inverse_total(self):
        for record in self:
            record.amount = record.total / 2.0

-------------------------------------------------------------
можно ссылаться на один метод compute в нескольких разных полях
-------------------------------------------------------------
Когда изменяется поле other_field, метод _compute_fields будет вызван,
и поля field1 и field2 будут пересчитаны на основе значения other_field.

from odoo import models, fields, api

class MyModel(models.Model):
    _name = 'my.model'

    field1 = fields.Integer(compute='_compute_fields')
    field2 = fields.Integer(compute='_compute_fields')

    @api.depends('other_field')
    def _compute_fields(self):
        # Выполняйте вычисления для field1 и field2
        for record in self:
            # Например, присвойте значения на основе other_field
            record.field1 = record.other_field * 2
            record.field2 = record.other_field * 3

-------------------------------------------------------------
сколько раз будет вызываться метод?
-------------------------------------------------------------

Метод compute будет вызван автоматически каждый раз, когда одно из полей, указанных в декораторе @api.depends, будет изменено.

Таким образом, если одно из полей, указанных в зависимостях @api.depends, изменяется, метод compute будет вызван для каждой записи (record), у которой изменилось одно из полей зависимостей. Это означает, что метод compute будет выполнен для каждой записи, удовлетворяющей условиям изменения полей, указанных в @api.depends.

Если изменяется несколько полей, указанных в зависимостях @api.depends, метод compute будет вызван только один раз для каждой записи, при условии, что все изменения происходят в рамках одной операции.

Важно отметить, что при использовании метода compute следует быть осторожным и избегать выполнения долгих операций внутри него, так как это может существенно замедлить производительность системы при обновлении большого количества записей.