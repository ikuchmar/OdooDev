
from odoo import fields, models, api

class Field(models.Model):
    _inherit = '_tu_helper.field'

    @api.multi
    def unlink(self):
        # do some additional actions
        res = super(Field, self).unlink()
        return res

# unlink
# Видаляє вибрані записи.
#
# def unlink(self):
#    for statement in self:
#        statement.line_ids.unlink()
#        next_statement = self.search([
# ('previous_statement_id', '=', statement.id),
# ('journal_id', '=', statement.journal_id.id)])
#        if next_statement:
#            next_statement.previous_statement_id = statement.previous_statement_id
#    return super(AccountBankStatement, self).unlink()
#
# Перевизначається для забезпечення цілісності даних, проведення додаткових дій с записами, що видаляються, обмеження видалення тощо.