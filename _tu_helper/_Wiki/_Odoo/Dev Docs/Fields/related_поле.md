
В Odoo релейтед (related) поле представляет собой поле модели, которое относится к другой модели
 и позволяет получить доступ к данным этой другой модели. 
Релейтед поле обычно используется,
 когда необходимо связать две модели и отобразить данные одной модели в другой.

Релейтед поле имеет два важных параметра:

поле-цель (target field), которое определяет поле, данные которого нужно отобразить;
модель-цель (target model), которая определяет модель, к которой относится поле-цель.
Пример использования релейтед поля в Odoo:

Предположим, у нас есть две модели:

==========================================================================
class Partner(models.Model):
    _name = 'res.partner'

    name = fields.Char(string='Name')
    is_company = fields.Boolean(string='Is a Company')
    country_id = fields.Many2one('res.country', string='Country')

==========================================================================
class Country(models.Model):
    _name = 'res.country'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')

==========================================================================
Мы можем создать релейтед поле "code" в модели "res.partner", которое будет отображать код страны из модели "res.country", используя следующий код:

class Partner(models.Model):
    _name = 'res.partner'

    name = fields.Char(string='Name')
    is_company = fields.Boolean(string='Is a Company')
    country_id = fields.Many2one('res.country', string='Country')

    country_code = fields.Related('country_id', 'code', string='Country Code')

В этом примере, мы создаем новое поле "country_code" в модели "res.partner", которое связано с полем "code" модели "res.country" через поле "country_id".

Теперь, когда мы получаем данные из модели "res.partner", мы можем использовать поле "country_code", чтобы получить код страны, связанной с этой моделью.