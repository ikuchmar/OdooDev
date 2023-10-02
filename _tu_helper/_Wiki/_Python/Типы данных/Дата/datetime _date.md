==========================================
преобразовать объект типа datetime в тип date - использовать атрибут .date() объекта datetime.
==========================================

from datetime import datetime

# Создание объекта datetime
datetime_obj = datetime(2023, 5, 19, 10, 30, 0)

# Преобразование объекта datetime в тип date
date_obj = datetime_obj.date()

print(date_obj)


# начало месяца
    date_from = fields.Date(string='Date from',
                            default=lambda self: datetime.now().replace(day=1, hour=0, minute=0, second=0))
                            
# сегодня
    date_to = fields.Date(string='Date to',
                          default=fields.Date.today())

# дата от сегодняшней даты
today_date = datetime.today().date()