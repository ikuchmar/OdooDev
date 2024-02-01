set (6, 0, ids)
=========================
Кортеж виглядає (6, 0, ids)
Другий параметр ігнорується, третій це список (це важливо, саме список) id записів.
Замінює поточний список зв’язків на переданий. Так якби очистити зв’язок і створити нові.
Важливо! Навіть якщо треба передати один id, все одно треба передавати список (список з одного елементу).
values['sale_line_ids'] = [(6, None, self.sale_line_ids.ids)]

    self.supplier_pizza_inn = self.env['lunch.supplier'].create({
    'partner_id': self.partner_pizza_inn.id,
    'send_by': 'mail',
    'automatic_email_time': 11,
    'available_location_ids': [
    (6, 0, [self.location_office_1.id, self.location_office_2.id])
    ],
    })