# -*- coding: utf-8 -*-
from datetime import date, timedelta, datetime
from itertools import groupby
from operator import itemgetter

from dateutil.relativedelta import relativedelta, SU

from odoo import _, fields, models, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools.misc import OrderedSet


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ===========================================================
    def get_locations_list_by_parent_location(self, location):
        # соберем все "подчиненные" локации
        stock_location_list = []
        stock_location_records = self.env['stock.location'].search([
            ('location_id', '=', location.id),
        ])

        # for record_sl in stock_location_records:
        #     stock_location_list.append(record_sl.id)

        stock_location_list = stock_location_records.ids
        stock_location_list.append(location.id)

        return stock_location_records.ids

    # ===========================================================
    def button_fill_move_ids_by_stock_quant(self):
        # соберем все "подчиненные" локации
        stock_location_list = self.get_locations_list_by_parent_location(self.location_id)

        stock_quant_records = self.env['stock.quant'].search([
            ('location_id', 'in', stock_location_list),
        ])

        # stock_quant_records.mapped('location_id')

        new_lines_list = []
        for record_sq in stock_quant_records:
            new_line = {
                'picking_id': self.id,
                'name': self.name,
                'product_id': record_sq.product_id.id,
                'product_uom_qty': record_sq.quantity,
                'product_uom': record_sq.product_id.uom_id.id,
                'lot_ids': (record_sq.lot_id.id,),
                'company_id': self.company_id.id,
                'date': self.date,
                'location_id': record_sq.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            }
            new_lines_list.append(new_line)

        self.move_ids.unlink()
        self.move_ids.create(new_lines_list)

        return

    # ===========================================================
    def button_clean_move_ids(self):
        self.move_ids.unlink()

        return

    # ким авто создание АМ по кнопке Подтвердить в SP (не называть функции кириллицей!!!!)
    def button_validate_delete(self):
        validate = super().button_validate()
        # ______________________________________________________
        # Custom code:
        # создание возвратного АМ
        for picking in self:
            if picking.note == '<p>storno</p>':  # TODO WTF?
                self.check_storno()
        # ______________________________________________________
        for picking in self:
            # ким нужно создавать АМ только если заполнен purchase_id (purchase.order)
            # в кнопке  (SP.Подтвердить) смущает - что там создается АМ - не проверяя что он уже есть
            # и вот в этом и проблема (только она проявилась не с РО, а с SO (при уже созданном АМ) - SP.Подтвердить - хочет создать еще один - а при создании проверка что нет строчек для АМ
            # if picking.purchase_id.requisition_id.payment_type == 'deferment':
            if picking.purchase_id:
                i = self.purchase_id.action_create_invoice()
                needed_account_move = self.env['account.move'].search([('id', '=', i['res_id'])])
                needed_account_move.action_post()
        # ______________________________________________________
        return validate

    # ким базовое поле из 15 - move_lines в stock.picking уже нет, вместо него поле move_ids
    # отключаю - сделал свою (выше)
    def button_validate(self):
        """ Переопределение стандартной функции button_validate чтобы:
        1. проверить if picking.note == 'storno'
            и сделать кастомное сторно

        2. проверить picking.purchase_id.requisition_id.payment_type == 'deferment':
            и сделать Инвойс на Закупку purchase_id.action_create_invoice()
            затем его завалидировать.

        """
        # Clean-up the context key at validation to avoid forcing the creation of immediate
        # transfers.
        ctx = dict(self.env.context)
        ctx.pop('default_immediate_transfer', None)
        self = self.with_context(ctx)

        # Sanity checks.
        if not self.env.context.get('skip_sanity_check', False):
            self._sanity_check()

        self.message_subscribe([self.env.user.partner_id.id])

        # Run the pre-validation wizards. Processing a pre-validation wizard should work on the
        # moves and/or the context and never call `_action_done`.
        if not self.env.context.get('button_validate_picking_ids'):
            self = self.with_context(button_validate_picking_ids=self.ids)
        res = self._pre_action_done_hook()
        if res is not True:
            return res

        # ______________________________________________________
        # Custom code:
        # TODO требуется переделать.
        #  А лучше вообще избавиться от этого кода и этой кастомизации
        for picking in self:
            if picking.note == '<p>storno</p>':  # TODO WTF?
                self.check_storno()
        # ______________________________________________________

        # Call `_action_done`.
        pickings_not_to_backorder = self.filtered(lambda p: p.picking_type_id.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.picking_type_id.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        pickings_not_to_backorder.with_context(cancel_backorder=True)._action_done()

        # ким создается АМ (на склад в пути)
        pickings_to_backorder.with_context(cancel_backorder=False)._action_done()

        if self.user_has_groups('stock.group_reception_report'):
            pickings_show_report = self.filtered(lambda p: p.picking_type_id.auto_show_reception_report)
            lines = pickings_show_report.move_ids.filtered(lambda
                                                               m: m.product_id.type == 'product' and m.state != 'cancel' and m.quantity_done and not m.move_dest_ids)
            if lines:
                # don't show reception report if all already assigned/nothing to assign
                wh_location_ids = self.env['stock.location']._search(
                    [('id', 'child_of', pickings_show_report.picking_type_id.warehouse_id.view_location_id.ids),
                     ('usage', '!=', 'supplier')])
                if self.env['stock.move'].search([
                    ('state', 'in', ['confirmed', 'partially_available', 'waiting', 'assigned']),
                    ('product_qty', '>', 0),
                    # ('reserved_qty', '>', 0),
                    ('location_id', 'in', wh_location_ids),
                    ('move_orig_ids', '=', False),
                    ('picking_id', 'not in', pickings_show_report.ids),
                    ('product_id', 'in', lines.product_id.ids)], limit=1):
                    action = pickings_show_report.action_view_reception_report()
                    action['context'] = {'default_picking_ids': pickings_show_report.ids}
                    return action
        # ______________________________________________________
        # TODO - нужно переписать: отнаследовать пикинг, обернуть эту функцию
        #  другой отдельной функцией, вызвать super, а потом этот код выполнить
        # Custom code:
        # Зачем? Добавьте описание данного функционала.
        for picking in self:
            # ким нужно создавать АМ только если заполнен purchase_id (purchase.order)
            # в кнопке  (SP.Подтвердить) смущает - что там создается АМ - не проверяя что он уже есть
            # и вот в этом и проблема (только она проявилась не с РО, а с SO (при уже созданном АМ) - SP.Подтвердить - хочет создать еще один - а при создании проверка что нет строчек для АМ
            # if picking.purchase_id.requisition_id.payment_type == 'deferment':

            if picking.purchase_id:
                # ким создается АМ (на поставщика)
                i = self.purchase_id.action_create_invoice()
                needed_account_move = self.env['account.move'].search([('id', '=', i['res_id'])])
                needed_account_move.action_post()
        # ______________________________________________________
        return True

    def check_storno(self):
        journal_id = self.env['account.journal'].search([('code', '=', 'РАХУН')], limit=1)

        storno_lines = {}
        for stock_move_id in self.move_ids_without_package:
            if not stock_move_id.move_line_ids:
                continue
            stock_move = self.env['stock.move.line'].search([
                ('lot_name', '=', stock_move_id.move_line_ids[0].lot_id.name),
                ('picking_code', '=', 'incoming'),
                ('location_usage', '=', 'supplier'),
                ('state', '=', 'done')], limit=1)
            # limit=1 Добавил потому что иногда бывает закупка одной и той же партии в одном ордере но разными лайнами
            purchase_order = stock_move.origin

            if not purchase_order:
                raise UserError(
                    f'Немає ордера на купівлю товара {stock_move_id.name} з партії {stock_move_id.move_line_ids[0].lot_id.name}')

            if not storno_lines.get(purchase_order):
                storno_lines[purchase_order] = []

            storno_lines[purchase_order].append({
                'product_id': stock_move_id.product_id.id,
                'name': stock_move_id.name,
                'quantity_done': stock_move_id.quantity_done,
                'product_qty': stock_move_id.product_qty,
                'barcode': stock_move_id.product_id.barcode
            })

        for storno_line in storno_lines:
            purchase_order_id = self.env['purchase.order'].search([('name', '=', storno_line)])

            account_move_invoice_id = purchase_order_id.invoice_ids.filtered(
                lambda p: not p.reversed_entry_id and p.state == 'posted')

            if not account_move_invoice_id:
                raise UserError(f'Не знайдено опублікованного рахунку для товару з ордера {storno_line}')

            # Если было уже сторно (в invoice_line_ids первичного АМ - указано reversed_entry_id
            # ----------------------------------------------------------------------------------
            account_move_storno_ids = purchase_order_id.invoice_ids.filtered(
                lambda p: p.reversed_entry_id and p.state == 'posted')

            if account_move_storno_ids:
                for account_move_storno_id in account_move_storno_ids:
                    for line in storno_lines[storno_line]:
                        invoice_storno_line = account_move_storno_id.invoice_line_ids.filtered(
                            lambda inv: inv.product_id.id == line['product_id'])
                        line['product_qty'] -= invoice_storno_line.quantity
                        # line['reserved_qty'] -= invoice_storno_line.quantity

            if not len(list(filter(lambda x: (x['product_qty'] > 0), storno_lines[storno_line]))):
                continue
            # ----------------------------------------------------------------------------------

            # вызов визарда создания АМ (возвратного)
            new_storno = self.env['account.move.reversal'].create({
                'refund_method': 'refund',
                'date_mode': 'custom',
                'journal_id': journal_id.id,
                'company_id': self.env.company.id,
                'currency_id': self.company_id.currency_id.id,
                'move_ids': [(4, account_move_invoice_id.id)]
            })
            # ким создастся новый АМ со AM_lines как в изначальном АМ
            # код ниже подменяет invoice_line_ids - оставляет только с заданным товаром
            action = new_storno.reverse_moves()
            new_account_move_storno_id = self.env['account.move'].search([('id', '=', action['res_id'])])
            invoice_lines = []
            for line in storno_lines[storno_line]:
                if line['product_qty'] > 0:
                    invoice_line = new_account_move_storno_id.invoice_line_ids.filtered(
                        lambda inv: inv.product_id.id == line['product_id'])
                    # invoice_line.quantity = line['product_qty'] if line['quantity_done'] > line['product_qty'] else \
                    #     line['quantity_done']
                    invoice_line.with_context(check_move_validity=False).write({
                        'quantity': line['product_qty'] if line['quantity_done'] > line['product_qty'] else line[
                            'quantity_done']
                    })
                    invoice_lines.append(invoice_line.id)
            # new_account_move_storno_id._recompute_dynamic_lines()
            new_account_move_storno_id.invoice_line_ids = [(6, 0, [id for id in invoice_lines])]

# def button_validate(self):
#     res = super(StockPicking, self).button_validate()
#     if self.purchase_id.requisition_id.payment_type == 'deferment':
#         i = self.purchase_id.action_create_invoice()
#         needed_account_move = self.env['account.move'].search([('id', '=', i['res_id'])])
#         needed_account_move.action_post()  # FIXME тут происходит лютая, кастомная дичь
#     return res
