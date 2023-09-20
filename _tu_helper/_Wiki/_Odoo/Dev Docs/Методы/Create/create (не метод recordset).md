===================================================
create (не метод recordset)
===================================================

Створює нові записи та повертає їх.
При создании объкта
Якщо використовується з @api.model_create_multi отримує список словників та повертає рекордсет створених записів.
Якщо використовується застаріла форма @api.model отримує словник і повертає створений об’єкт
Поля, значення яких не були передані, будуть заповнені значеннями за замовчуванням.

Важливо, якщо при виклику не були передані обов’язкові поля і вони не мають визначених значень за замовчуванням, це призвиде до помилки.

--------------------------------------------------
после create - write сам не вызовется
(вызовется если вызовут write)

===================================================
 Перевизначається для доповнення параметрів або виконання дій з новоствореними записами.
===================================================

    @api.model
    def create(self, vals_list):

        if 'payment_account_id' in vals_list:
            account = self.env['account.account'].browse(vals_list['payment_account_id'])

        if not account.reconcile:
           account.reconcile = True

    return super().create(vals_list)

===================================================
При создании объекта - создается новый объект в другой моделе
===================================================

    @api.model
    def create(self, vals_list):
        new_record = super().create(vals_list)

        if 'personal_doctor_id' not in  vals_list:
            return new_record

        self.env['personal.doctor.history'].create({
            'doctor_id': vals_list['personal_doctor_id'],
            'patient_id': new_record.id,
            ' date_medication ': fields.date.today(),
        })

        return new_record

==========================================================
Метод создания записи:
===================================================

    @api.model
    def create(self, vals):
        record = super(MyModel, self).create(vals)
        # do some additional actions
        return record

В этом примере мы создаем метод create в модели MyModel. Этот метод переопределяет метод create в родительской модели. 
Метод create создает новую запись в модели на основе значений, переданных в параметре vals. 
Затем он выполняет дополнительные действия и возвращает созданную запись.



===================================================
(добавление новых значений зависимых от введенных (альтернатива компьютид)
обращаем внимание что все ссылочные поля - получают только id (integer)
если нужно получить значение через точку - сначала нужно их найти

warehouse_id_int = vals['warehouse_id_2']
(self.env['stock.warehouse'].browse(warehouse_id_int))
===================================================

    @api.model
    def create(self, vals):

        # поиск analytic_tag в warehouse
        warehouse_id_int = vals.get('warehouse_id_2', False)
        warehouse_id = self.env['stock.warehouse'].browse(warehouse_id_int)

        analytic_tag_id = warehouse_id.analytic_tag_id
        analytic_tag_int = analytic_tag_id.id

        # заполнение analytic_tag в шапке
        vals_new['analytic_tag_id'] = analytic_tag_int

        return super().create(vals_new)