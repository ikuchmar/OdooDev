 //Первую строку листа передать (5, 0, 0)], # Очищает все строки в line_ids
 а потом добавить остальные (0, 0, ids)

bill = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'date': self.date,
            'mo_approval_id': self.id,
            'not_for_1c': True,
            'move_type': 'in_invoice',
            'partner_bank_id': self.partner_id.bank_ids and self.partner_id.bank_ids[0].id or False,
            'invoice_line_ids': [ (5, 0, 0)],  # Очищает все строки в line_ids
                                  (0, 0, {'product_id': r.product_id.id,
                                         'quantity': r.quantity,
                                         # 'analytic_tag_ids': r.analytic_tag_ids.ids,
                                         'analytic_distribution': {r.analytic_account_id.id: 100.0, },
                                         'product_uom_id': r.product_uom_id.id,
                                         'price_unit': r.price_unit}) for r in self.product_line_ids]
        })


