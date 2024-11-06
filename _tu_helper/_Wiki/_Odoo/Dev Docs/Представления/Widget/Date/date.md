date (FieldDate)
===================================
Это тип поля по умолчанию для полей типа date. Обратите внимание, что он также работает с полями datetime. При форматировании дат использует часовой пояс текущего сеанса.

Поддерживаемые типы полей: date, datetime
Параметры:

datepicker: дополнительные настройки для виджета * datepicker widget*.

    <field name="datefield" options='{"datepicker": {"daysOfWeekDisabled": [0, 6]}}'/>

datetime (FieldDateTime)
===================================
Это тип поля по умолчанию для полей типа datetime.

Поддерживаемые типы полей: date, datetime
Параметры:

datepicker: дополнительные настройки для виджета * datepicker widget*.

    <field name="datetimefield" options='{"datepicker": {"daysOfWeekDisabled": [0, 6]}}'/>

daterange (FieldDateRange)
===================================
Этот виджет позволяет пользователю выбрать начальную и конечную дату в одном селекторе.

Поддерживаемые типы полей: date, datetime
Параметры:

related_start_date: применяется к полю даты окончания, чтобы получить значение даты начала, которое используется для отображения диапазона в селекторе.
related_end_date: применить к полю даты начала, чтобы получить значение даты окончания, которое используется для отображения диапазона в селекторе.
picker_options: дополнительные настройки для селектора.

    <field name="start_date" widget="daterange" options='{"related_end_date": "end_date"}'/>