# append

- скорее всего неправильно, правильно update
============================================

        result.append({'name': move_line.name,
                    'move_id': self.id,
                    'account_id': move_line.account_id,
                    'analytic_account_id': move_line.analytic_account_id,
                    'analytic_tag_ids': analytic_tag_id,
                    'debit': abs(new_amount if new_amount < 0 else 0),
                    'credit': abs(new_amount if new_amount > 0 else 0),
                    'amount_currency': new_amount * -1,
                    'currency_id': move_line.currency_id,
                    'journal_id': move_line.journal_id,
                    'partner_id': move_line.partner_id,
                    'period': move_line.period,
                    'product_id': move_line.product_id,
                    'product_uom_id': move_line.product_uom_id,
                    'purchase_id': move_line.purchase_id,
                    'purchase_line_id': move_line.purchase_line_id,
                    'purchase_order_id': move_line.purchase_order_id,
                    'quantity': move_line.quantity,
                    'price_unit': round((new_amount / move_line.quantity), 2) if move_line.quantity else new_amount,
                    'price_total': round(move_line.price_total, 2),
                    'price_subtotal': round(move_line.price_subtotal, 2),
                    'product_uom_category_id': move_line.product_uom_category_id,
                    'sale_line_ids': move_line.sale_line_ids,
                    'statement_id': move_line.statement_id,
                    'statement_line_id': move_line.statement_line_id,
                    'tax_fiscal_country_id': move_line.tax_fiscal_country_id,
                    'tax_group_id': move_line.tax_group_id,
                    'tax_ids': move_line.tax_ids,
                })