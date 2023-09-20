==========================================================
@api.returns
==========================================================
Визначає записи якої моделі має повернути метод.

@api.model ????

@api.returns('ir.module.module')
def get_module_list(self):
   states = ['to upgrade', 'to remove', 'to install']
   return self.env['ir.module.module'].search([('state', 'in', states)])
