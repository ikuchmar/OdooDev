     # создание новой записи в stock.picking
     # (не понял что такое Form, и где create)
     # stock.return.picking - wizard (Транцидентная модель), которая создает stock.picking
     
stock_return_picking = Form(self.env['stock.return.picking'].sudo().with_context(
                            active_id=picking.id, active_model='stock.picking'))

     # сохранение формы..?
     stock_return_picking = stock_return_picking.save()

В данном коде используется модуль Form из библиотеки odoo.addons.base.models.ir_ui_view для создания и сохранения новой записи модели stock.return.picking.

stock_return_picking = Form(...): Здесь создается новый экземпляр объекта формы для модели stock.return.picking.

self.env['stock.return.picking']: Создается запрос к модели stock.return.picking через self.env, чтобы получить доступ к этой модели.

.sudo(): Метод sudo() используется для выполнения операции суперпользователя (администратора). Это позволяет обойти ограничения прав доступа и выполнить операцию с полными правами доступа.

.with_context(active_id=picking.id, active_model='stock.picking'): Метод with_context() используется для установки дополнительных значений контекста. В данном случае, устанавливаются значения active_id и active_model для контекста. Значение picking.id устанавливается для ключа active_id в контексте, чтобы указать текущий активный идентификатор записи stock.picking. Значение 'stock.picking' устанавливается для ключа active_model в контексте, чтобы указать модель текущей активной записи stock.picking.

stock_return_picking.save(): После того, как форма была сконфигурирована, вызывается метод save() для создания и сохранения новой записи модели stock.return.picking с учетом параметров, указанных в форме. После выполнения этой строки кода будет создана новая запись модели stock.return.picking с параметрами, которые были указаны в форме.

Общий смысл этого кода состоит в том, чтобы создать новую запись модели stock.return.picking, передав информацию о текущей активной записи stock.picking через контекст с учетом полномочий суперпользователя (администратора). Затем используется метод save() для сохранения созданной записи.


Метод save() используется в контексте модели формы Form для создания или обновления записи модели базы данных на основе значений, которые были заданы в форме.
Когда вы работаете с формой с помощью Form, вы можете задавать значения полей, определенных в модели, а затем вызвать метод save() для сохранения этих значений в базе данных. 
Если запись существует (то есть имеет уникальный идентификатор), метод save() обновит значения полей для этой записи. Если запись не существует, то есть это новая запись, 
метод save() создаст новую запись с указанными значениями полей.

from odoo import models

class MyWizard(models.TransientModel):
    _name = 'my.wizard'

    def do_something(self):
        # Создаем новую форму для модели stock.return.picking
        stock_return_picking = Form(self.env['stock.return.picking'])

        # Задаем значения полей в форме
        stock_return_picking.reason = 'Some reason'
        stock_return_picking.picking_id = self.env['stock.picking'].browse(1)

        # Вызываем метод save() для сохранения значений в базе данных
        new_picking_return = stock_return_picking.save()

        # new_picking_return теперь содержит созданную или обновленную запись stock.return.picking
В этом примере мы создаем новую форму для модели stock.return.picking, задаем значения полей reason и picking_id и вызываем метод save(), чтобы создать или обновить запись в модели базы данных stock.return.picking.

Важно отметить, что метод save() возвращает созданную или обновленную запись, поэтому вы можете сохранить этот результат в переменную для дальнейшего использования, как в примере выше с переменной new_picking_return.





