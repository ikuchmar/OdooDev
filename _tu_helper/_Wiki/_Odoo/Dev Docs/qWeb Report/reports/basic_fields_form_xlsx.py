from odoo import api, fields, models, _
import logging
import xlsxwriter
import base64


class StornoForm(models.AbstractModel):
    _name = 'report._tu_helper.basic_fields_form'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, docs):
        header_1 = workbook.add_format({'font_name': 'Arial', 'bold': True, 'size': '14', 'align': 'center',
                                        'valign': 'vcenter', 'text_wrap': 1, 'text_wrap': 1, 'bottom': 2})
        style_1 = workbook.add_format({'font_name': 'Arial', 'size': '9', 'align': 'left', 'text_wrap': 1,
                                       'underline': True})
        style_2 = workbook.add_format({'font_name': 'Arial', 'size': '9', 'align': 'left', 'text_wrap': 1,
                                       'bold': True})

        row = 1
        col = 1

        # add new line in f-string
        nl = '\n'

        for obj in docs:
            report_name = obj.field_char
            # One sheet by doc
            sheet = workbook.add_worksheet(report_name[:31])
            sheet.set_column('A:A', 1.29)
            sheet.set_column('B:AH', 1.89)
            sheet.set_column('AI:AL', 4.0)
            sheet.set_row(0, 10.8)
            sheet.set_row(1, 21)
            sheet.set_row(2, 10.8)
            sheet.set_row(3, 13.6)
            sheet.set_row(4, 12)
            sheet.set_row(5, 3.6)
            sheet.set_row(6, 12.6)
            sheet.set_row(7, 48.6)
            sheet.set_row(8, 3.6)
            sheet.set_row(9, 12.6)
            sheet.set_row(10, 3.6)
            sheet.set_row(11, 12)
            sheet.set_row(12, 12)

            sheet.merge_range(row, col, row, col+36,
                              f"Тест поля даты: {report_name} від {obj.get_date_formated(obj.field_date)}",
                              header_1)
            row += 2
            sheet.merge_range(row, col, row, col + 5, "Тест іnt поля: ", style_1)
            col += 6
            sheet.merge_range(row, col, row, col + 30, obj.field_integer, style_2)
            row += 3
            col = 1
            sheet.merge_range(row, col, row, col + 5, "Тест text поля: ", style_1)
            col += 6
            sheet.merge_range(row, col, row, col + 30, obj.field_text, style_2)


