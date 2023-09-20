# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
import logging
import xlsxwriter
import base64

import os
import tempfile
import shutil
from datetime import datetime

from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DismissalOrderInherits(models.Model):
    _name = 'hr.contract'
    _inherit = ['hr.contract', 'stupid.numeration.mixin']

    transfer_contract = fields.Boolean(string='transfer', default=False)

    number_dismisal = fields.Char(string='number', copy=False, required=False)

    result_data_xlsx = fields.Binary('Result XLSX', attachment=True, copy=False)
    result_filename_xlsx = fields.Char(copy=False)

    reasons_for_dismissal = fields.Selection([('38', 'Voluntary dismissal'), ('36', 'Dismissal by agreement of the parties')], string='Reason for Dismissal')
    grounds_for_dismissal = fields.Char(string='Grounds for Dismissal')
    outgoing_assistance = fields.Boolean(string='Outgoing assistance')
    sum_outgoing_assistance = fields.Float(string='Sum of outgoing assistance')

    # Add tracking in fields:
    job_id = fields.Many2one('hr.job', compute='_compute_employee_contract', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Job Position',
        tracking=True)
    department_id = fields.Many2one('hr.department', compute='_compute_employee_contract', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string="Department",
        tracking=True)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",
        tracking=True)

    @api.onchange('number_dismisal')
    def _onchange_number_dismisal(self):
        numbers = ['0']
        all_contract = self.env['hr.contract'].search([])
        # TODO rewrite me: а если их накопиться миллион? Почему не было сделать serch(domain) ?
        contract = all_contract.filtered(lambda l: l.id != self.id.origin)
        for con in contract:
            if con.number:
                numbers.append(con.number)
            if con.number_dismisal:
                numbers.append(con.number_dismisal)
            # if con.transfer_number:
            #     numbers.append(con.transfer_number)
        # TODO rewrite me: а если их накопиться миллион? Почему не было сделать serch(domain) ?
        this_contract = all_contract.filtered(lambda l: l.id == self.id.origin)
        if this_contract:
            if this_contract.number:
                numbers.append(this_contract.number)
            # if this_contract.transfer_number:
            #     numbers.append(this_contract.transfer_number)
        # TODO rewrite-me please
        clear_num = self.stupid_sort_by_number(numbers)
        self.stupid_check_update_doc_number('number_dismisal', clear_num)

    @api.onchange('number')
    def _onchange_number(self):
        numbers = ['0']
        all_contract = self.env['hr.contract'].search([])
        # TODO rewrite me: а если их накопиться миллион? Почему не было сделать serch(domain) ?
        contract = all_contract.filtered(lambda l: l.id != self.id.origin)
        for con in contract:
            if con.number:
                numbers.append(con.number)
            if con.number_dismisal:
                numbers.append(con.number_dismisal)
            # if con.transfer_number:
            #     numbers.append(con.transfer_number)
        # TODO rewrite me: а если их накопиться миллион? Почему не было сделать serch(domain) ?
        this_contract = all_contract.filtered(lambda l: l.id == self.id.origin)
        if this_contract:
            if this_contract.number_dismisal:
                numbers.append(this_contract.number_dismisal)
            # if this_contract.transfer_number:
            #     numbers.append(this_contract.transfer_number)
        # TODO rewrite-me please
        clear_num = self.stupid_sort_by_number(numbers)
        self.stupid_check_update_doc_number('number', clear_num)

    def make_dismissal_order(self):
        date_now = datetime.today().strftime('%d.%m.%Y')

        result_data_xlsx = False
        result_filename_xlsx = "default.xlsx"
        path = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        os.chdir(temp_dir)
        workbook = xlsxwriter.Workbook(result_filename_xlsx)
        worksheet = workbook.add_worksheet()

        style1 = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'size': '9', 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1,
             'border': 0})
        style2 = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'size': '9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1,
             'bottom': 1})
        style3 = workbook.add_format(
            {'font_name': 'Arial', 'bold': False, 'size': '9', 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1,
             'bottom': 0})
        style4 = workbook.add_format(
            {'font_name': 'Arial', 'bold': False, 'size': '8', 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1,
             'bottom': 0})
        style5 = workbook.add_format(
            {'font_name': 'Arial', 'bold': False, 'size': '9', 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1,
             'border': 1})
        style6 = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'size': '9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1,
             'border': 1})
        style7 = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'size': '9', 'align': 'left', 'valign': 'vcenter', 'text_wrap': 1,
             'bottom': 1})
        style8 = workbook.add_format(
            {'font_name': 'Arial', 'bold': True, 'size': '11', 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1,
             'bottom': 0})
        style9 = workbook.add_format(
            {'font_name': 'Arial', 'bold': False, 'size': '9', 'align': 'center', 'valign': 'vcenter', 'text_wrap': 1,
             'border': 1})

        worksheet.set_column(0, 33, 2.67)

        worksheet.set_row(0, 12)
        worksheet.set_row(1, 12)
        worksheet.set_row(2, 12)
        worksheet.set_row(3, 12)
        worksheet.set_row(4, 12)
        worksheet.set_row(5, 12)
        worksheet.set_row(6, 12)
        worksheet.set_row(7, 12)
        worksheet.set_row(8, 15)
        worksheet.set_row(9, 15)
        worksheet.set_row(10, 15)
        worksheet.set_row(11, 12)
        worksheet.set_row(12, 12)
        worksheet.set_row(13, 12)
        worksheet.set_row(14, 12)
        worksheet.set_row(15, 12)
        worksheet.set_row(16, 12)
        worksheet.set_row(17, 12)
        worksheet.set_row(18, 6)
        worksheet.set_row(19, 12)
        worksheet.set_row(20, 12)
        worksheet.set_row(21, 3.75)
        worksheet.set_row(22, 12)
        worksheet.set_row(23, 12)
        worksheet.set_row(24, 3)
        worksheet.set_row(25, 12)
        worksheet.set_row(26, 12)
        worksheet.set_row(27, 3.75)
        worksheet.set_row(28, 12)
        worksheet.set_row(29, 12)
        worksheet.set_row(30, 12)
        worksheet.set_row(31, 12)
        worksheet.set_row(32, 12)
        worksheet.set_row(33, 12)
        worksheet.set_row(34, 12)
        worksheet.set_row(35, 12)
        worksheet.set_row(36, 12)
        worksheet.set_row(37, 12)
        worksheet.set_row(38, 12)
        worksheet.set_row(39, 12)
        worksheet.set_row(40, 12)

        history = self.env['hr.contract.turbo.history'].search([('contract_id', '=', self.id)])
        if len(history.ids) > 1:
            last_contract = history[-1]
        else:
            last_contract = history
        worksheet.merge_range('Y1:AH1', 'Типова форма N П-4', style1)
        worksheet.merge_range('A2:U3', self.company_id.name, style2)
        worksheet.merge_range('A4:U4', 'Найменування підприємства (установи, організації) ', style4)
        worksheet.merge_range('Y2:AH4', 'ЗАТВЕРДЖЕНО наказом Держкомстату України від 5 грудня 2008 р. N 489 ', style3)
        worksheet.merge_range('C5:D5', 'м. Київ', style3)
        worksheet.merge_range('V6:Z6', 'Код  ЄДРПОУ', style5)
        worksheet.merge_range('AA6:AG6', self.company_id.company_registry, style6)
        worksheet.merge_range('V7:Z7', 'Дата складання', style5)
        if not self.order_date_dismiss:
            raise UserError('Не заповнено дату на звільнення')
        worksheet.merge_range('AA7:AG7', self.order_date_dismiss.strftime('%d.%m.%Y'), style6)
        worksheet.merge_range('M9:P9', 'НАКАЗ №', style8)
        worksheet.merge_range('Q9:X9', self.number_dismisal, style7)
        worksheet.merge_range('M10:T10', '(РОЗПОРЯДЖЕННЯ)', style8)
        worksheet.merge_range('I11:Y11', 'про припинення трудового договору (контракту)', style8)
        worksheet.merge_range('B13:D13', 'Звільнити', style1)
        if self.date_end:
            worksheet.merge_range('F13:L13', self.date_end.strftime('%d.%m.%Y'), style3)
        else:
            worksheet.merge_range('F13:L13', ' ', style3)
        worksheet.merge_range('Z14:AG14', 'Табельний номер', style9)
        worksheet.merge_range('Z15:AG15', self.employee_id.registration_number, style6)
        worksheet.merge_range('B17:AG17', self.employee_id.name, style2)
        worksheet.merge_range('B18:AG18', "(прізвище, ім'я, по батькові) ", style4)
        worksheet.merge_range('B20:AG20', last_contract.department_id.name, style2)
        worksheet.merge_range('B21:AG21', 'назва структурного підрозділу', style4)
        worksheet.merge_range('B23:AG23', last_contract.job_id.name, style2)
        worksheet.merge_range('B24:AG24', 'назва професії (посади), розряд, клас (категорія) кваліфікації', style4)
        worksheet.merge_range('B26:AG26', dict(self._fields['reasons_for_dismissal']._description_selection(self.env)).get(self.reasons_for_dismissal), style2)
        worksheet.merge_range('B27:AG27', '(причина звільнення)', style4)
        worksheet.merge_range('B29:AG29', self.grounds_for_dismissal, style2)
        worksheet.merge_range('B30:AG30', '(підстави звільнення)', style4)
        if self.outgoing_assistance == True:
            sum = list(str(self.sum_outgoing_assistance))
            worksheet.write('B32', 'X', style6)
            worksheet.merge_range('J32:M32', ''.join(list(str(self.sum_outgoing_assistance))[:-3]), style2)
            worksheet.merge_range('P32:S32', ''.join(list(str(self.sum_outgoing_assistance))[-2:]), style2)
        else:
            worksheet.write('B32', ' ', style6)
            worksheet.merge_range('J32:M32', '0', style2)
            worksheet.merge_range('P32:S32', '00', style2)
        worksheet.merge_range('D32:H32', 'Вихідна допомога', style3)
        worksheet.merge_range('N32:O32', 'грн.', style3)
        worksheet.merge_range('T32:U32', 'коп.', style3)
        worksheet.merge_range('B34:H34', 'Виплатити компенсацію за', style3)
        vacation_compensation = self.employee_id.allocation_count - self.employee_id.allocation_used_count
        worksheet.merge_range('J34:K34', vacation_compensation, style2)
        worksheet.merge_range('L34:X34', 'днів невикористаної основної щорічної відпустки', style3)
        worksheet.merge_range('B37:H37', 'Керівник підприємства', style1)
        worksheet.merge_range('M37:R37', ' ', style2)
        manager = self.env['hr.department'].search([('code', '=', 'ADM')])
        if manager:
            worksheet.merge_range('U37:AG37', manager.manager_id.name, style2)
        else:
            worksheet.merge_range('U37:AG37', ' ', style2)
        worksheet.merge_range('M38:R38', '(підпис) ', style4)
        worksheet.merge_range('U38:AG38', 'П. І. Б.', style4)
        worksheet.merge_range('B40:J40', 'З наказом (розпорядженням)', style1)
        worksheet.merge_range('B41:F41', 'ознайомлений', style1)
        worksheet.merge_range('M40:R40', ' ', style2)
        worksheet.merge_range('M41:R41', '(підпис працівника)', style4)
        worksheet.write('U41', '"', style3)
        worksheet.write('V41', ' ', style2)
        worksheet.write('W41', '"', style3)
        worksheet.merge_range('X41:AC41', ' ', style2)
        worksheet.write('AD41', '20', style3)
        worksheet.merge_range('AE41:AF41', ' ', style2)
        worksheet.merge_range('AG41:AH41', 'року', style3)

        workbook.close()

        data_file = open(result_filename_xlsx, "rb")
        result_data_xlsx = base64.b64encode(data_file.read())
        data_file.close()
        os.chdir(path)
        shutil.rmtree(temp_dir)
        self.update({
            'result_data_xlsx': result_data_xlsx,
            'result_filename_xlsx': "Наказ_на_звільнення.xlsx"
        })

