from odoo import fields, models


class Fields(models.Model):
    _inherit = '_tu_helper.field'

    field_image = fields.Image(string='Image',
                               max_width=1920,
                               max_height=720,
                               verify_resolution=True,
                               attachment=True,
                               help='This is Image field')


    # max_width -  the maximum width of the image (default: 0, no limit)
    # (максимальная ширина картинки)

    # max_heidht - the maximun height of the image  (default: 0, no limit)
    # (максимальная высота картинки)

    # Якщо зображення має більші розміри воно буде автоматично стиснуте до вказаних
    # На формі має вигляд сабнейлу завантаженого зображення з кнопками редагування або видалення

    # verify_resolution - whether the image resolution should be verified to ensure it doesn’t go over the maximum image resolution (default: True)
    # (должно ли изображение проверяться на предмет того, не выходит ли оно на рамки уставленных размеров)

    #  attachment -  whether the field should be stored as ir_attachment or in a column of the model’s table (default: True).
    #  (должно ли поле храниться как ir_attachment или в столбце таблицы модели (по умолчанию: True).)

    #   help - подсказка при наведении пользователем на поле


