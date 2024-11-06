@api.constrains
==========================================================
Використовується для перевірки правильності введених даних.
Є альтернативою до _sql_constraints, але не діє на рівні СУБД і може бути проігнорований

    @api.constrains('vat', 'country_id')
    def check_vat(self):
       for partner in self:
           country = partner.commercial_partner_id.country_id
           if partner.vat and self._run_vat_test(partner.vat, country) is False:
               partner_label = _("partner [%s]", partner.name)
               msg = partner._build_vat_error_message(
                    country and country.code.lower() or None, partner.vat, partner_label)
               raise ValidationError(msg)

Важливо, таке обмеження спрацьовує лише за умови, якщо в вказані поля передаються значення.
Тобто у викликах create або write ці поля є в переліку.

@api.constrains
==========================================================
Декоратор @api.constrains используется при СОХРАНЕНИИ для добавления ограничений (валидаторов) на поля модели.
Функция, декорированная @api.constrains, будет вызываться каждый раз, когда изменяется значение одного или нескольких
полей, указанных в аргументах декоратора. Если условие не выполняется, функция должна вызывать исключение
ValidationError, чтобы отменить
операцию сохранения.

Основные моменты:
Используется для проверки значений полей.
Вызывается автоматически при изменении указанных полей.
Если условие не выполняется, генерируется исключение ValidationError.

    from odoo import models, fields, api
    from odoo.exceptions import ValidationError
    
    class ExampleModel(models.Model):
    _name = 'example.model'
    
        field_a = fields.Integer()
        field_b = fields.Integer()
    
        @api.constrains('field_a', 'field_b')
        def _check_fields(self):
            for record in self:
                if record.field_a < 0:
                    raise ValidationError("Field A must be non-negative")
                if record.field_b > 100:
                  raise ValidationError("Field B must be less than or equal to 100")

Когда использовать @api.constrains (а не write (или create))
==========================================================
теоретически, можно выполнять те же проверки, что и в @api.constrains, в методе write (или create). Однако,
использование @api.constrains предоставляет более чистый и декларативный способ реализации валидации полей, который
лучше интегрируется с механизмом ORM Odoo

Использование @api.constrains более предпочтительно для валидации полей, поскольку:
- Это декларативный способ, который делает код более читаемым и понятным.
- Валидации через @api.constrains автоматически применяются при любых изменениях полей, независимо от того, как они
происходят (через форму, импорт данных, массовое обновление и т.д.).
- Код в методах write и create может стать загроможденным, если использовать их для всех проверок.

