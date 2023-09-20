        bill = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'date': self.date,
            'mo_approval_id': self.id,
            'not_for_1c': True,
            'move_type': 'in_invoice',
            'partner_bank_id': self.partner_id.bank_ids and self.partner_id.bank_ids[0].id or False,
            'invoice_line_ids': [(0, 0, {'product_id': r.product_id.id,
                                         'quantity': r.quantity,
                                         # 'analytic_tag_ids': r.analytic_tag_ids.ids,
                                         'analytic_distribution': {r.analytic_account_id.id: 100.0, },
                                         'product_uom_id': r.product_uom_id.id,
                                         'price_unit': r.price_unit}) for r in self.product_line_ids]
        })

===============================================================================================
        new_invoice_line_ids = []
        for location_id, amount_total in totals_by_warehouses_dict.items():
            new_invoice_line = (0, 0, {
                'product_id': self.product_id.id,
                'tax_ids': [(6, 0, self.product_id.taxes_id.ids)],
                'analytic_distribution': analytic_distribution,
                'period': self.period.id,
                'quantity': 1,
                'price_unit': amount_total,  # Поменяйте это на то, что нужно
                'product_uom_id': self.product_id.uom_id.id,
            })
            new_invoice_line_ids.append(new_invoice_line)

        new_move = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'name': '',
            'sell_requisition_id': self.requisition_id.id,
            'is_service': True,
            'invoice_line_ids': new_invoice_line_ids,
        })

