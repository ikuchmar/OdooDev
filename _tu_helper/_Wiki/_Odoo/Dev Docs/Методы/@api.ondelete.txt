==========================================================
@api.ondelete
==========================================================
Альтернатива перевизначенню методу unlink. Має параметр at_uninstall,
який визначає робити перевірки в залежності від того іде нормальна робота модуля чи модуль деінсталюється

@api.ondelete(at_uninstall=False)
def _unlink_only_if_open(self):
   for statement in self:
       if statement.state != 'open':
           raise UserError(_(
'In order to delete a bank statement, you must first cancel '
'it to delete related journal items.'))