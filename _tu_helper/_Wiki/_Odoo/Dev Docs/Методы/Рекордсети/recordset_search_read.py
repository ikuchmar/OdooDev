from odoo import fields, models, api

class AModel(models.Model):
    _name = 'a.model'

    # self.sudo().search_read([["key", "in", opts]],["key", "value"])
    #
    # @api.model
    # def search_read(self, domain=None, fields=None, offset=0,
    #                 limit=None, order=None):

    # --------------------
    # search_read
    # -------------------
    # Повертає список словників, з вказаними у параметрі fields полями.
    # Інші параметри аналогічні search.
    # domain - домен пошуку, якщо передати [] (пустий список) поверне всі записи
    # fields - список полів, які будуть ключами у словниках
    # offset (int) - кількість рядків від початку вибірки, що буде проігнорована, для сторінкової обробки
    # limit(int) - обмеження по кількості рядків
    # order(str) - правило сортування, назви полів та порядок desc або asc (другий за замовчанням)
    #
