states
========================
Словник правил, що змінюють значення параметрів readonly, required, invisible в залежності від значення у полі state.

       partner_id = fields.Many2one(
           'res.partner', string='Customer', readonly=True,
           states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
           required=True, change_default=True, index=True, tracking=1,
           domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    
       state = fields.Selection(
           required=True, default='disabled', selection=[
            ('draft', 'Draft'), ('sent', 'Sent'),
            ('test', 'Test Mode')], )

Важливо: поле state має бути не лише обов’язково додано в модель для використання з цим параметром, але й виведене на
користувацький інтерфейс


