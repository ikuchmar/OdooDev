create
===============================
    new_partner = self.env['res.partner'].create({
        'name': 'John Doe',
        'email': 'johndoe@example.com',
        'phone': '1234567890'
    })


create с заполнением поля line_ids
===============================
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',  # Указываем тип счета-фактуры, например, "out_invoice" (исходящая счет-фактура)
            'partner_id': self.env['res.partner'].search([], limit=1).id,  # Партнер для примера, можно заменить на нужный
            'invoice_date': fields.Date.today(),
            'line_ids': [
                (0, 0, {
                    'account_id': self.env['account.account'].search([('user_type_id.type', '=', 'receivable')], limit=1).id,
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 100.0,
                    'debit': 0.0,
                    'credit': 100.0,
                }),
                (0, 0, {
                    'account_id': self.env['account.account'].search([('user_type_id.type', '=', 'receivable')], limit=1).id,
                    'name': 'Product B',
                    'quantity': 1,
                    'price_unit': 200.0,
                    'debit': 100.0,
                    'credit': 0.0,
                }),
            ]
        })
        return move
