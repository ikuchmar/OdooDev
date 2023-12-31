метод strftime() (string format time) - позволяет определить формат строки вывода, включая дату, время и другие
компоненты времени.

import datetime

# Создание объекта datetime

datetime_obj = datetime.datetime.now()

# strftime - Дата в Строку

formatted_string = datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

print(formatted_string)
Результат выполнения кода будет содержать текущую дату и время в формате "ГГГГ-ММ-ДД ЧЧ:ММ:СС", например:

формат "%Y-%m-%d %H:%M:%S" для представления даты и времени. Каждый символ в формате имеет своё значение, например "%Y"
представляет год в четырехзначном формате, "%m" представляет месяц, "%d" представляет день, а "%H", "%M" и "%S"
представляют часы, минуты и секунды соответственно.

Вы можете выбрать нужный вам формат, сочетая различные символы формата. Более подробную информацию о символах формата
можно найти в документации Python: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior

"2023-09-12 14:30:00" в datetime 
=====================================
    from datetime import datetime
    
    # Исходная строка с датой и временем
    date_string = "2023-09-12 14:30:00"
    
    # Задайте формат, который соответствует вашей строке
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Преобразование строки в объект datetime
    date_object = datetime.strptime(date_string, date_format)
    
    print(date_object)

 '20231114074453179' в datetime 
========================================
    def str_to_datetime(date_string):
        try:
            # Преобразование строки в объект datetime
            date_object = datetime.strptime(date_string, '%Y%m%d%H%M%S%f')
            return date_object
        except ValueError:
            # В случае ошибки возвращаем None или можно обработать исключение по вашему усмотрению
            return None