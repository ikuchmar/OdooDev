mapped - отримати список значень визначеного поля
===================================================
 Для полів зв’язків буде отриманий рекордсет.
 Аби отримати список значень слід вказати просте поле.

    product_list = self.requisition_id.line_ids.mapped('product_id')
    records.mapped('name')
    records.mapped('partner_id')

    
можно через точку
===================================================================
    product_list = self.requisition_id.line_ids.mapped('product_id.name')
    records.mapped('partner_id.id')
    records.mapped('partner_id.bank_ids')
    
 Можна використати функцію, щоб отримати комбінацію значень полів
===================================================================
    records.mapped(lambda r: r.field1 + r.field2)


чтобы получить МНОГО полей - как список кортежей
===================================================================
    returns_data = returns.mapped(lambda rec: (rec.location_id.name, rec.amount_total))

    am_line_list = am_line_records.mapped(lambda rec:
                                                  (rec,
                                                   rec.move_id,
                                                   rec.move_id.warehouse_id,
                                                   rec.move_id.warehouse_id.analytic_account_id,
                                                   rec.price_total))


список кортежей, где каждый кортеж будет содержать имя склада (location_id.name) и общую сумму???? (amount_total) 
для каждой записи в коллекции returns.



mapped() - преобразования значений полей в записях одной модели в новые значения с использованием функции-обработчика.
===================================================================
преобразования данных на уровне модели базы данных.

mapped(field_name, function)

field_name - имя поля, значения которого нужно преобразовать. Это может быть имя поля модели или относительный путь к полю (например, "partner_id.name" для доступа к полю "name" модели "partner_id").
function - функция-обработчик, которая будет применяться к значениям поля. Эта функция должна быть определена в модели и принимать один аргумент - значение поля, которое будет преобразовано.

class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Sales Order'

    name = fields.Char(string='Order Reference', required=True)
    amount_total = fields.Float(string='Total Amount', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)

    # Пример использования метода mapped()
    def update_order_status(self):
        # Обновление статуса заказа на основе общей суммы
        for order in self:
            if order.amount_total > 1000:
                order.state = 'confirmed'
            else:
                order.state = 'done'

    def print_order(self):
        # Пример использования метода mapped() для преобразования
        # значений полей перед печатью заказа
        self.mapped('name', lambda name: 'Order Reference: ' + name)
        self.mapped('amount_total', lambda amount: 'Total Amount: ' + str(amount))
        self.mapped('state', lambda state: 'Status: ' + state)
        # Операции печати заказа...
В данном примере метод mapped() используется для преобразования значений полей модели sale.order перед печатью заказа. Функции-обработчики, переданные в метод mapped(), применяются к значениям полей name, amount_total и state, чтобы добавить соответствующие префиксы и суффиксы к значениям полей перед печатью.


