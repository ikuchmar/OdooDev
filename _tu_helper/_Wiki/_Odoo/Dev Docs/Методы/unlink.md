==========================================================
unlink *
==========================================================
Видаляє вибрані записи.

def unlink(self):
   for statement in self:
       statement.line_ids.unlink()
       next_statement = self.search([
('previous_statement_id', '=', statement.id),
('journal_id', '=', statement.journal_id.id)])
       if next_statement:
           next_statement.previous_statement_id = statement.previous_statement_id
   return super(AccountBankStatement, self).unlink()

Перевизначається для забезпечення цілісності даних, проведення додаткових дій с записами, що видаляються, обмеження видалення тощо.


==========================================================
Метод удаления записи: unlink *
==========================================================

@api.multi
def unlink(self):
    # do some additional actions
    res = super(MyModel, self).unlink()
    return res

В этом примере мы создаем метод unlink в модели MyModel.
Этот метод переопределяет метод unlink в родительской модели.
Метод unlink удаляет текущую запись из модели.
Затем он выполняет дополнительные действия и возвращает результат выполнения родительского метода.

==========================================================

record = self.env[model_name].browse(record_id)  # Получаем запись по id
if record:
    record.unlink()  # Удаляем запись
else:
    # Обработка случая, если запись не найдена
    # в данной модели с указанным id
    pass
