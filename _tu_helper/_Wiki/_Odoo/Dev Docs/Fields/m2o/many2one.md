

    field_many2one_id = fields.Many2one(string='Many2one field',
                                        comodel_name='basic.fields',
                                        required=True,
                                        check_company=True,
                                        auto_join=True,
                                        ondelete='cascade')

string
=======================================================================
    – the label of the field seen by users; if not set, the ORM takes the field name in the class (capitalized).
    #    (метка поля, видимая пользователями; если не установлено, ORM берет имя поля в классе (с заглавной буквы).

domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
=======================================================================
    (обмежує перелік об’єктів, що можуть бути вибрані. Список кортежів або метод моделі, що повертає список кортежів.)

    #    comodel_name – name of the target model Mandatory except for related or extended fields.
    #    (имя целевой модели Обязательно, за исключением связанных или расширенных полей.)

    #    required -  требуется заполнение значения

    #    check_company – Mark the field to be verified in _check_company().
    #    Add a default company domain depending on the field attributes.
    #    (Отметьте поле для проверки в _check_company(). Добавьте домен компании по умолчанию в зависимости от атрибутов поля.)

    #    auto_join - whether JOINs are generated upon search through that field (default: False)
    #    генерируются ли JOIN при поиске по этому полю (по умолчанию: False)

    #    store
    #    Логічний. Визначає, чи буде поле зберігатись у БД. Обчислювальні поля за замовчуванням не зберігаються

    #    related
    #    Строкове. Послідовність назви полів: поле даної моделі, що посилається на іншу, через точку поле в моделі, на яке посилається дане поле
    #    survey_id = fields.Many2one('survey.survey', related='job_id.survey_id', string="Survey", readonly=True)

    #    context - an optional context to use on the client side when handling that field
    #    (необязательный контекст для использования на стороне клиента при обработке этого поля)

    #    delegate – set it to True to make fields of the target model accessible from the current model (corresponds to _inherits)
    #    (установите значение True, чтобы сделать поля целевой модели доступными из текущей модели (соответствует _inherits))

    #    ondelete – what to do when the referred record is deleted; possible values are: 'set null', 'restrict', 'cascade'
    #    (что делать, когда упомянутая запись удалена; возможные значения: 'установить ноль', 'ограничить', 'каскад')



    #    states
    #   Словник правил, що змінюють значення параметрів readonly, required, invisible в залежності від значення у полі state.
    #
    #   partner_id = fields.Many2one(
    #       'res.partner', string='Customer', readonly=True,
    #       states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
    #       required=True, change_default=True, index=True, tracking=1,
    #       domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    #
    #   state = fields.Selection(
    #       required=True, default='disabled', selection=[
    #        ('draft', 'Draft'), ('sent', 'Sent'),
    #        ('test', 'Test Mode')], )
    #
    #   Важливо: поле state має бути не лише обов’язково додано в модель для використання з цим параметром, але й виведене на користувацький інтерфейс
    #
    #   company_dependent
    #   Логічний. Важливий параметр для правильної роботи режиму мультикомпанії. Встановлює залежність поля від поточної компанії користувача.
    #   Значення поля зберігається у зовнішній моделі ir.property.
    #
    #
    #


