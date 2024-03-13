
 Перед записью
 ==========================================================
    
     def write(self, vals):
         self.my_field = value

         return super().write(vals)


После записи
==========================================================

    def write(self, vals):
        res = super().write(vals)

        self.my_field = value
        return res

Метод изменения записи:
==========================================================
    @api.multi
    def write(self, vals):
        res = super(MyModel, self).write(vals)

        # do some additional actions
        return res

В этом примере мы создаем метод write в модели MyModel. Этот метод переопределяет метод write в родительской модели.
Метод write изменяет значения полей записи, указанных в параметре vals.
Затем он выполняет дополнительные действия и возвращает результат выполнения родительского метода.

