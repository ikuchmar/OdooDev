Отримує список id або один id і повертає рекордсет записів, що відповідають цим id
====================================================================================

    acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

Використовується, щоб отримати об’єкт на цілочисельне значення id.


    analytic_account_id = self.env['account.analytic.account'].browse(int(dict_key))


    to_analytic_account = fields.Many2one(
        'account.analytic.account', string='Analytic Account (to)', required=True,
        default=lambda self: self.env['account.analytic.account'].browse([223]))
