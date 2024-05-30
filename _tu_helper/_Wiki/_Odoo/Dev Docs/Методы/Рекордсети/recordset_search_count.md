# Получение количества записей, соответствующих домену
    record_count = self.env['stock.move.line'].search_count(domen)




from odoo import fields, models, api

class AModel(models.Model):
    _name = 'a.model'

    @api.model
    def search_count(self, args):
        res = self.search(args, count=True)
        return res if isinstance(res, int) else len(res)


    # --------------------
    # search_count
    # -------------------
    #  Це попередня функція з параметром count=True
    #
    #
    #


