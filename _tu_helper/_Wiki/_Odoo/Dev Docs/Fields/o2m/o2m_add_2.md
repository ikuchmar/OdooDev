Чтобы добавить новую строку в поле invoice_line_ids в модели account.move в системе Odoo, вам потребуется создать новую запись для модели account.move.line, которая связана с вашей записью журнала проводок account.move. Вот пример кода на Python, который демонстрирует, как это можно сделать:

python
Copy code
# Предполагается, что вы уже находитесь в среде, где доступен env

# Получите объект account.move, к которому вы хотите добавить строку
move = env['account.move'].browse(move_id)  # move_id - ID нужной записи account.move

# Создайте новую строку счета-фактуры
line_vals = {
    'move_id': move.id,
    'name': 'Название продукта или услуги',
    'quantity': 1,
    'price_unit': 100.0,
    'account_id': account_id,  # ID счета, который должен быть использован для строки
}

# Добавление новой строки в invoice_line_ids
new_line = env['account.move.line'].create(line_vals)

# Сохраняем изменения, если нужно сделать это явно
move.write({'invoice_line_ids': [(4, new_line.id)]})
В этом примере:

move_id — это идентификатор записи журнала, к которому вы хотите добавить строку.
name, quantity, price_unit, account_id — значения, которые вы хотите задать для новой строки. Вы должны заменить их актуальными данными.
(4, new_line.id) в методе write говорит о том, что нужно добавить существующую запись (не создавая новую), связывая её ID с текущим account.move.
Обязательно убедитесь, что у вас есть правильные доступы и идентификаторы для создания записей.

User
можно ли добавить строку непосредственно в поле invoice_line_ids не создавая запись в модель account.move.line ?
ChatGPT
В системе Odoo поле invoice_line_ids в модели account.move связывает каждую запись журнала проводок с одной или несколькими записями account.move.line. Это поле представляет собой одно из типов полей отношений в Odoo, называемое One2many. Природа поля One2many такова, что оно не хранит сами данные, а лишь предоставляет ссылку на строки в связанной модели. В вашем случае, это модель account.move.line.

Добавить строку непосредственно в invoice_line_ids без создания записи в account.move.line технически невозможно, потому что Odoo требует, чтобы данные сначала были созданы в связанной модели (account.move.line). Только после этого можно создать связь в поле One2many (invoice_line_ids).

Другими словами, чтобы добавить новую строку счета-фактуры, вы должны:

Создать запись в модели account.move.line.
Связать эту запись с нужной записью account.move через поле invoice_line_ids.
Это стандартное поведение Odoo для управления данными через поля One2many и Many2one, гарантирующее целостность и правильное управление данными в базе.

User
я бы хотел добавить несколько записей в invoice_line_ids сразу, а не по одной 
ChatGPT
Если вам нужно добавить несколько записей в invoice_line_ids сразу, вы можете воспользоваться командой (0, 0, {...}), которая создаёт новые записи непосредственно в связанной модели и сразу же добавляет их к текущей записи. Эта команда позволяет создавать новые строки на лету без предварительного создания объектов в модели account.move.line. Вот как это можно сделать:

python
Copy code
# Предполагается, что вы уже находитесь в среде, где доступен env

# Получите объект account.move, к которому вы хотите добавить строки
move = env['account.move'].browse(move_id)  # move_id - ID нужной записи account.move

# Список значений для создания новых строк счета-фактуры
line_vals_list = [
    {
        'name': 'Товар 1',
        'quantity': 1,
        'price_unit': 150.0,
        'account_id': account_id_1,  # Замените на актуальный ID счета
    },
    {
        'name': 'Услуга 2',
        'quantity': 2,
        'price_unit': 200.0,
        'account_id': account_id_2,  # Замените на актуальный ID счета
    }
]

# Добавление новых строк в invoice_line_ids с помощью команды (0, 0, {...})
commands = [(0, 0, line_vals) for line_vals in line_vals_list]
move.write({'invoice_line_ids': commands})
В этом примере:

Каждый элемент в line_vals_list представляет значения для создания новой строки.
Команда (0, 0, line_vals) используется в методе write для создания и немедленного добавления новой строки в invoice_line_ids. Здесь (0, 0, {...}) означает создание новой записи с данными, указанными в словаре.
Этот метод позволяет эффективно добавить множество новых строк одним вызовом, упрощая обработку и сокращая количество кода, необходимого для создания каждой строки отдельно.

User
при этом те строки, которые были перед моими действиями останутся в invoice_line_ids? т.е. мои записи затрут исходные или добавят к существующим?
ChatGPT
Когда вы используете команду (0, 0, {...}) в контексте поля One2many в Odoo, новые строки добавляются к существующим записям в этом поле, не затирая и не удаляя их. Это значит, что если у вас уже были строки в поле invoice_line_ids перед вашим действием, они останутся на месте, а новые строки будут добавлены к ним.

Таким образом, при использовании команд в форме:

python
Copy code
move.write({'invoice_line_ids': [(0, 0, line_vals)]})
вы просто добавляете новые строки к уже существующим в invoice_line_ids, не изменяя или не удаляя предыдущие строки. Это позволяет динамично расширять список строк счета-фактуры без потери уже введенной информации.

Если ваша цель — изменить или удалить существующие строки перед добавлением новых, для этого есть другие команды:

(1, ID, {...}) для обновления существующей записи с указанным ID.
(2, ID) или (3, ID) для удаления существующей записи с указанным ID (с различиями в обработке каскадных удалений).
Использование этих команд позволяет точно контролировать содержимое поля invoice_line_ids в зависимости от ваших нужд.