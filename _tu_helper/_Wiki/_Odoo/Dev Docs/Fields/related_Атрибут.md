поля (fields) позволяют определять атрибуты моделей и их типы данных,
которые используются для хранения и управления данными в базе данных.
Одним из таких полей является fields.Integer, которое представляет целочисленные значения.

Кроме того, в Odoo также есть возможность создавать связи между различными моделями с помощью релейтед (related) полей,
которые позволяют получать данные из других моделей. Релейтед поле определяется с помощью параметра related в определении поля.
Поле через точку с поля м2о
Можно куча точек
После такого объявление в ру файле - их можно показывать на хмл
    
      sick_type_color = fields.Integer(related='sick_id.sick_type_id.color')
    
      sick_type_id = fields.Many2one(related='sick_id.sick_type_id')

с опцией сторедж - они будут сохраняться

==========================================================================

Например, если мы хотим создать релейтед поле типа fields.Integer,
которое будет отображать значения из другой модели, мы можем использовать следующий код:

class SaleOrderLine(models.Model):
    _name = 'sale.order.line'

    product_template_id = fields.Many2one('product.template', string='Product Template')
    product_template_qty = fields.Integer(string='Product Template Quantity', related='product_template_id.qty_available')

В этом примере мы создаем модель SaleOrderLine и добавляем поле product_template_qty,
которое является релейтед полем типа fields.Integer и связано с полем qty_available в модели product.template.
Когда мы будем получать значения product_template_qty из экземпляра SaleOrderLine,
они будут отображать значения поля qty_available из связанной модели product.template.

==========================================================================
related на Selection
==========================================================================
journal_type = fields.Selection(related='move_id.journal_id.type',
                                  store=True)


