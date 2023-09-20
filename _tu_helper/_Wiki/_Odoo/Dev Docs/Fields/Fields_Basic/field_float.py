from odoo import fields, models


class FieldBasic(models.Model):
    _inherit = 'tu_helper.field_basic'

    field_float = fields.Float(string="Float 1",
                               digits=(10, 3),
                               required=True,
                               default=0,
                               store=True,
                               help='This is float field')

    # --------------------------------------------------------------------------------------
    # Float - Поле з плаваючою комою.
    # --------------------------------------------------------------------------------------
    # To round a quantity with the precision of the unit of measure:
    # (Чтобы округлить количество с точностью до единицы измерения:)
    # fields.Float.round(self.product_uom_qty, precision_rounding=self.product_uom_id.rounding)

    # To check if the quantity is zero with the precision of the unit of measure:
    # (Чтобы проверить, равно ли количество нулю с точностью до единицы измерения:)
    # fields.Float.is_zero(self.product_uom_qty, precision_rounding=self.product_uom_id.rounding)

    # To compare two quantities:
    # (сравнить две величины:)
    # field.Float.compare(self.product_uom_qty, self.qty_done, precision_rounding=self.product_uom_id.rounding)

    # --------------------------------------------------------------------------------------
    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

    # digits – The optional parameter digits defines the precision and scale of the number.
    # (Необязательный параметр digits определяет точность и масштаб числа.)
    # Має вигляд пари (загально символів, символів після коми) або рядок, що посилається на  запис DecimalPrecision, наприклад 'Product Price' або 'Payment Terms'
    # price = fields.Float(
    #     string='Price', compute='_compute_price',
    #     digits='Product Price', readonly=False, store=True)
    # Через специфіку формату запису та зберігання, числа з плаваючою комою існують проблеми з порівнянням, округленням тощо,
    # Тому прямо в класі Float є методи, які вирішують ці проблеми
    # round - округлює до заданої точності за правилами математичного округлення
    # >>> fields.Float.round(1.45, 1)
    # 1.5
    # >>> fields.Float.round(1.35, 1)
    # 1.400
    # is_zero - перевіряє рівність 0 у заданій точності
    # >>> fields.Float.is_zero(0.000123, 3)
    # True
    # fields.Float.is_zero(0.000123, 5)
    # False
    # compare - порівнює два числа у заданій точності
    # >>> fields.Float.compare(0.12345, 0.123, 2)
    # 0
    # fields.Float.compare(0.12345, 0.123, 4)
    # 1

    # The precision is the total number of significant digits in the number (before and after the decimal point), the scale is the number of digits after the decimal point.
    # (Точность — это общее количество  цифр в числе (до и после запятой), масштаб — это количество цифр после запятой.)
    # If the parameter digits is not present, the number will be a double precision floating point number.
    # Если цифры параметра отсутствуют, число будет числом с плавающей запятой двойной точности.

    # required -  требуется заполнение значения

    # default -  значение поля по умолчанию

    # help - подсказка при наведении пользователем на поле
