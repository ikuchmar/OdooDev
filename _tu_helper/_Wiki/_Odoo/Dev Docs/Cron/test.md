# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - Warning: Warning Exception to use with raise
# To return an action, assign: action = {...}

# env.cr.execute("""
#   UPDATE ir_config_parameter SET value='False' WHERE key='web.base.production_mode';
#   UPDATE ir_config_parameter SET value='*' WHERE key='edin_service.password';
#   UPDATE ir_config_parameter SET value='*' WHERE key='mo.turbosms.token';
#   UPDATE ir_config_parameter SET value='21612b26-90b0-468f-bd15-234bdaeaea17' WHERE key='tranzoo.api_key';
#   UPDATE ir_config_parameter SET value='QWhxYlE3bldLN2N4NHlySDZKaTFlcWt6' WHERE key='tranzoo.api_secret';
#   UPDATE ir_config_parameter SET value='84936ebb-fb45-48ef-9d72-e450bf764649' WHERE key='tranzoo.pos_id';
#   UPDATE ir_config_parameter SET value='*' WHERE key='database.secret';
#   UPDATE ir_config_parameter SET value='stplatformstage.odoo' WHERE key='sftp_tools.login';
#   UPDATE ir_config_parameter SET value='2s7vSUPtfcNETxv6+9Tm9jjazc1mOqGF' WHERE key='sftp_tools.password';
#   UPDATE ir_config_parameter SET value='stplatformstage.blob.core.windows.net' WHERE key='sftp_tools.server';
# """)

# env.cr.execute("""
#   DELETE FROM public.ir_ui_view_custom;
#   DELETE FROM public.ir_ui_view_group_rel;
#   DELETE FROM public.ir_ui_view WHERE model = 'sale.order' or model = 'purchase.order' or model = 'account.move' or model = 'purchase' or model = 'hr_employee' or model = 'hr_employee' or name = 'product_template_form_view_ds';
# """)

# env['ir.asset'].search([('path', '=', '/web/static/src/scss/webclient.scss')]).unlink()
# env.cr.commit()

# dev = env['account.asset'].sudo().search([])
# for d in dev:
#     am = d.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
#     for a in am:
#         try:
#             a.unlink()
#         except Exception as e:
#             raise UserError(e)

# act_d = env['account.asset'].search([('state', '=', 'draft')])

# for act in act_d:
#   act.write({
#     'account_depreciation_id': 27,
#     'account_depreciation_expense_id': 307,
#     'journal_id': 17,
#     'prorata_date': act.create_date
#   })
#   act.validate()

# inventory = env['stock.inventory'].search([('analytic_tag_id', '=', False)])
# inventory.write({
#   'analytic_tag_id': 11
# })

# p = env['account.move'].search([('id', '=', 472376)])
# p.write({
#   'edin_verify': False
# })

# fill days in SO
# sale_order_ids = env['sale.order'].search([
#   ('state', '!=', 'draft'), 
#   ('state', '!=', 'cancel')
#   ])
# for order in sale_order_ids:
#   if (not order.date_order_hour or not order.day_of_week) and order.date_order:
#     order.write({})

# env['hr.contract.history'].migrate_to_new_model()

# attr = env['product.attribute.value'].search([('url_name', '=', False)])

# for att in attr:
#   url = att.prepare_url_name(att.name)
#   ser = env['product.attribute.value'].search([('url_name', '=', url)])
#   if ser:
#     att.write({
#       'url_name': att.prepare_url_name(att.name) + '2'
#     })
#   else:
#     att.write({
#       'url_name': att.prepare_url_name(att.name)
#     })

#couriers = env['hr.employee'].sudo().search([('id', 'in', [104, 124, 151])])
#env['res.partner'].sudo()._kagorta_evaluate()
#product_ids = env['product.template'].search([])
#for product_id in product_ids:
#  product_id.write({"name_for_search": product_id.with_context(lang="en_US").name})

#line = env['account.financial.html.report.line'].search([('code', '=', 'DEP_COPY')])
#
#line.write({
#   'financial_report_id': 4
#})

#raise UserError(line.financial_report_id)

#order = env['purchase.order'].search([('id', 'in', [5892])])
#order.write({
# 'edin_status': 'done'
#})

#order = env['purchase.order'].search([('name', '=', 'P08028')])
#order[0].write({
# 'edin_status': 'ordrsp',
# 'state': 'sent'
#})

# picking = env['stock.picking'].search([('name','=','ДННАБ/OUT/00709')])
# if picking:
#   #for move in picking.move_ids_without_package:
#   picking.write({
#       'date_done': '2022-01-28'
#     })

# перегенерировать урлы для товаров
# env['product.template'].update_products_translit()

# перегенерировать урлы для торговых марок
# env['mo_products_extend.trademarks'].update_trademarks_translit()

# перегенерировать урлы для категорий
# env['product.public.category'].update_categories_translit()

# перегенерировать урлы для видов товара
# env['mo_openapi_catalog.product_type'].update_products_type_translit()

# пересчитать остатки на складе
# env['product.template'].search([]).compute_warehouses()

# env.cr.execute("""
# UPDATE stock_picking SET name = 'Транзит ШУМ-АХМАТ 1'where id = 23063
# """)

# env['product.template'].get_published_catalog("ru_RU",{"count":12,"page":1},"","",1,True,[],[])

# item = env['product.pricelist.item'].search([('product_tmpl_id','=',8741),('final_price','=',68.00)])
# if item:
#     item.write({
#       'final_price': 59.90
#     })

# product.pricelist.item(19978, 11557)
# product_pricelist_item = env['product.pricelist.item'].search([('id','=',11557)])
# if product_pricelist_item:
#  product_pricelist_item.unlink()
  # for line in sale.order_line:
  #   if line.product_id.id == 9710:
  #     line.write({
  #       'changed_qty': 1
  #     })

# env.cr.execute("""
# DELETE FROM hr_payslip where id = 583
# """)

# questions = env['survey.question'].search([])
# for q in questions:
#   q.write({
#     'description': False
#   })
# env.cr.execute("""
# DELETE FROM res_partner where id = 126
# """)

# partner = env['res.partner'].search([('id','=',1606)])
# if partner:
#   partner.write({
#     'name': ' '
#   })


# env.cr.execute("""
# DELETE FROM stock_move_line where picking_id = 639 AND lot_id = 1498
# """)

# paket = env['product.template'].search([('id', '=', 8043)])
# search_order = env['sale.order'].search([('id','=',298)])
# sale_order_line = env['sale.order.line'].create({
#     'order_id': search_order.id,
#     'product_id': paket.product_variant_id.id,
#     'name': paket.name,
#     'product_uom_qty': 1,
#     'price_unit': 3.5
# })
# search_order.write({
#     'order_line': [(4, sale_order_line.id)]
# })

# search_sale_order = env['sale.order'].search([('id','=',841)])
# search_sale_order.write({
#   'last_status_history_id': False
# })


# price = env['product.pricelist'].search([('id','=',1)])
# price.recompute_prices()

# env.cr.execute("""
# UPDATE
# res_users
# SET is_courier = True
# WHERE id in (131,277,140,132,229,250,278,93,109)
# """)

# env.cr.execute("""
# UPDATE
# hr_employee
# SET delivered_order = False
# WHERE id = 35
# """)

# employee = env['hr.employee'].browse(35)
# if employee:
#   employee.write({
#     'delivered_order': False
#   })

# products = env['product.template'].search([])
# for product in products:
#   product.write({
#     'available_warehouses': False
#   })

# quants = env['product.template'].search([])
# for quant in quants:
#   quant.compute_warehouses()

# order = env['sale.order'].search([('courier_id','=',19)])
# for ord in order:
#   ord.write({
#     'with_courier': False
#   })

# env.cr.execute("""
# UPDATE
# uom_uom
# SET factor = 2
# WHERE id = 46
# """)

# breaks = env['mo_courier_statuses.break_history'].search([('employee_id', '=', 19), ('state', '=', 'active')])
# breaks[0].unlink()

# Вывести курьера из перерыва (удалить историю перерыва! должна остаться 1 запись чтобы можно было выйти из перерыва, иначе придется вручную) 
# breaks = env['mo_courier_statuses.break_history'].search([('employee_id', '=', 86), ('state', '=', 'active')])
# raise UserError(breaks)
# if breaks:
#  breaks[0].unlink()

# Вывести курьера из перерыва (изменить статус на свободный)
#employee = env['hr.employee'].search([('id','=',57)])
#raise UserError(employee.state)
#if employee:
#  employee.write({
#   'state': 'free'
#  })


# status_history = env['courier.sale_order_status_history'].search([('order_id', '=', 841), ('state', '=', 'sale'), ('state_out_time', '=', False)])
# if status_history:
#   status_history.unlink()

# order = env['sale.order'].search([('id','=',669)])
# if order:
#   order.write({
#     'with_courier': False
#   })
    
# employee = env['hr.employee'].search([('id','=',35)])
# if employee:
#   employee.write({
#     'state': 'free'
#   })

# for product in products:
#   product.write({
#     'can_use_tc': 'money'
#   })

# env.cr.execute("""
# DELETE FROM purchase_requisition where id = 105
# """)


# env.cr.execute("""
# delete from purchase_order where id = 20
# """)

# test_debit = env['account.account'].search([('id','=',2)])
# if test_debit:
#   test_debit.write({
#     'opening_debit': 0
#   })

# products = env['product.template'].search([('id','!=',0)])
# for product in products:
#   product.write({
#     'tracking': 'lot',
#     'use_expiration_date': True
#   })