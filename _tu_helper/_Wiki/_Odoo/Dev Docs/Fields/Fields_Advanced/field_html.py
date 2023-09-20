from odoo import fields, models


class AdvancedFields(models.Model):
    _inherit = '_tu_helper.field'

    field_html = fields.Html(string='Html',

                             translate=True,
                             sanitize=False,
                             sanitize_tags=False,
                             sanitize_attributes=False,
                             sanitize_style=False,
                             strip_style=True,
                             help='This is Html field')

    # --------------------------------------------------------------------------------------
    #  Html -  Довгий текст, що розширений роботою з html. Відображається на форі як wysiwyg редактора.
    # Може мати пусте значення. Має такі параметри.
    # Параметри
    # sanitize, sanitize_tags, sanitize_attributes, sanitize_style, strip_style, strip_classes
    # --------------------------------------------------------------------------------------
    # string – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    # ( метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

    # sanitize - whether value must be sanitized (default: True)
    # (нужно ли очищать значение)

    # sanitize_tags - whether to sanitize tags (only a white list of attributes is accepted, default: True)
    # (очищать ли теги (принимается только белый список атрибутов, по умолчанию: True)

    # sanitize_attributes - whether to sanitize attributes (only a white list of attributes is accepted, default: True)
    # очищать ли атрибуты (принимается только белый список атрибутов, по умолчанию: True)

    # sanitize_style - whether to sanitize style attributes (default: False)
    # очищать ли атрибуты стиля (по умолчанию: False)

    # strip_classes – whether to strip classes attributes (default: False)
    # удалять ли атрибуты классов (по умолчанию: False)

    # strip_style - whether to strip style attributes (removed and therefore not sanitized, default: False)
    # (следует ли удалять атрибуты стиля (удалены и, следовательно, не очищены, по умолчанию: False))

    # attachment - whether the field should be stored as ir_attachment or in a column of the model’s table (default: True).
    # (должно ли поле храниться как ir_attachment или в столбце таблицы модели (по умолчанию: True).)

    # copy - – whether the field value should be copied when the record is duplicated (следует ли копировать значение поля при дублировании записи)
    # (default: True for normal fields, False for one2many and computed fields, including property fields and related fields)
    # (следует ли копировать значение поля при дублировании записи
    # (по умолчанию: True для обычных полей, False для one2many и вычисляемых полей, включая поля свойств и связанные поля)))

    # store - – whether the field is stored in database (default:True, False for computed fields)
    # (хранится ли поле в базе данных (по умолчанию: True, False для вычисляемых полей))

    # help - подсказка при наведении пользователем на поле


