from odoo import fields, models, api

class AModel(models.Model):
    _name = 'a.model'


    # request.env['place'].sudo().search([
    #     ('is_shown_on_mobile','=',True),
    #     ('is_checkpoint','=',False),
    #     ('primary_category_id','!=',False),
    #     ('latitude','!=', False),('longtitude','!=', False),
    #     '|', ('active','=', True),('active','=',False)]))

    # --------------------
    # Домени пошуку
    # -------------------
    # Домени пошуку являють собою список кортежів та операторів зв’язку
    # Важливо! Доменом є саме список цих елементів. Окремий кортеж не є доменом.
    # [('name','=','ABC'),('language.code','!=','en_US'),
    # '|', ('сountry_id.code','=', 'be'),('country_id.code','=','de')]
    #
    # [('name','=','ABC')]
    # Окремий кортеж умови складається з трьох елементів
    # Назва поля, причому для полів типу Many2one можна використовувати поля зі зв’язаної моделі partner_id.country.
    # [('partner_id.country_id.code','=','ABC')]
    # Другим елементом є оператор, третім значення сумісне з оператором та полем. Наприклад, число, дата, список або рядок.
    #
    # Важливо! Якщо ми створюємо умову для поля Many2one треба передавать числове значення id, а не поле.
    #
    # Неправильно
    #
    # [('partner_id','=',self.partner_id)]
    #
    # Правильно
    #
    # [('partner_id','=',self.partner_id.id)]
    #
    #
    #
    #
    #
    #

