# expression в модуле odoo.osv 

предоставляет набор инструментов для создания и компоновки выражений доменов, которые
используются для фильтрации записей при выполнении операций чтения или поиска в базе данных Odoo.

Вот несколько основных классов и функций в модуле expression:

# expression.AND: 
Представляет логическое "И" (AND) выражение, которое объединяет несколько условий. Все условия должны
быть выполнены, чтобы запись была выбрана.

# expression.OR: 
Представляет логическое "ИЛИ" (OR) выражение, которое объединяет несколько условий. Запись будет выбрана,
если хотя бы одно из условий истинно.

# expression.NOT: 
Представляет логическое "НЕ" (NOT) выражение, которое инвертирует результат другого выражения.

# expression.TRUE_DOMAIN: 
Представляет домен, который всегда истинен, то есть не применяет фильтрацию.

# expression.FALSE_DOMAIN: 
Представляет домен, который всегда ложен, то есть не выбирает ни одной записи.

# expression.normalize_domain: 
Функция для нормализации домена, приводящая его к стандартному виду.

# expression.expression: 
Функция для создания произвольного выражения, используемого в домене.


Обратите внимание, что условия передаются в виде списка списков (каждый элемент списка представляет одно
условие в формате кортежа). Выражение expression.AND объединяет все условия логическим "И" (AND).

# "AND" для объединения всех условий
    from odoo.osv import expression
    
    condition1 = [('field1', '=', 'value1')]
    condition2 = [('field2', '>', 100)]
    condition3 = [('field3', '!=', False)]

    domain = expression.AND([condition1, condition2, condition3])

    print(domain)



# expression AND и OR:  (condition1 AND condition2) AND (condition3 OR condition4)
    from odoo.osv import expression
    
    condition1 = [('field1', '=', 'value1')]
    condition2 = [('field2', '>', 100)]
    condition3 = [('field3', '!=', False)]
    condition4 = [('field4', '!=', 'value4')]
    
    and_condition = expression.AND([condition1, condition2])

    or_condition = expression.OR([condition3, condition4])

    final_domain = expression.AND([and_condition, or_condition])

    print(final_domain)

