import openpyxl


# Установите библиотеку: "openpyxl"  в cmd: pip install openpyxl

# =============================================================
def set_new_value(key):
    dict_value = {"НомерДата": "ДатаНомер",
                  "Док1С": "Док2С",
                  "Док1СНомер": "Док2СНомер"}

    newValue = dict_value.get(key)

    if newValue == None:
        return value
    else:
        return newValue


# =============================================================
def main():
    path_file_template = r"C:\Users\Naomi\Downloads\n.xlsx"

    path_file_report = r"C:\Users\Naomi\Downloads\n2.xlsx"

    xls_wb = openpyxl.load_workbook(path_file_template)

    xls_sheet = xls_wb['TDSheet']

    xls_rows = tuple(xls_sheet.rows)

    for xls_row in xls_rows:
        for xls_sell in xls_row:
            key = xls_sheet[xls_sell.coordinate].value
            newValue = set_new_value(key)

            xls_sheet[xls_sell.coordinate].value = newValue
        break

    xls_wb.save(path_file_report)


# =============================================================
if __name__ == '__main__':
    main()
