@api.model_create_multi
==========================================================

Спеціальний декоратор, для метода create.
Після реалізації множинного створення (для збільшення швидкодії) потрібен для зворотної сумісності зі старим стилем,
коли в create передається словник, а не список словників.

    @api.model_create_multi
    def create(self, values_list):
       for values in values_list:
           if 'acquirer_id' in values:
               acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
    
               # Include acquirer-specific create values
               values.update(self._get_specific_create_values(acquirer.provider, values))
           else:
               pass  # Let psycopg warn about the missing required field
