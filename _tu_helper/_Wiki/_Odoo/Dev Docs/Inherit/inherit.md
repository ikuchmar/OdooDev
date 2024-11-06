В Odoo, _inherit используется для расширения существующих моделей. Есть несколько способов использования _inherit, в
зависимости от того, какую модель или функцию вы хотите расширить. Давайте рассмотрим основные варианты использования _
inherit.

# Наследование существующей модели

Этот способ используется для добавления новых полей или методов к существующей модели.

      class InheritedModel(models.Model):
      _inherit = 'existing.model' # Замените 'existing.model' на имя модели, которую вы хотите расширить
      
          new_field = fields.Char(string="New Field")
      
          def new_method(self):
              # Реализация нового метода
              pass


# Наследование существующего представления (view)

Этот способ используется для добавления новых полей или виджетов к существующему представлению модели.

      <odoo>
         <record id="view_inherited_form" model="ir.ui.view">
            <field name="name">existing.model.form.inherited</field>
            <field name="model">existing.model</field>
            <field name="inherit_id" ref="existing_module.view_existing_model_form"/>
            <field name="arch" type="xml">
               <xpath expr="//field[@name='field_name']" position="after">
               <field name="new_field"/>
               </xpath>
            </field>
         </record>
      </odoo>

# Наследование модели и изменения поведения

Можно использовать _inherit для изменения поведения существующих методов модели.

      class InheritedModel(models.Model):
      _inherit = 'existing.model'
      
          @api.multi
          def existing_method(self):
              # Дополнительная логика перед вызовом оригинального метода
              result = super(InheritedModel, self).existing_method()
              # Дополнительная логика после вызова оригинального метода
              return result



# Наследование модели с заменой (override)

Этот способ используется для полной замены существующего метода или поведения.

      class InheritedModel(models.Model):
      _inherit = 'existing.model'
      
          def existing_method(self):
              # Полная замена метода
              return "New behavior"

# Наследование с изменением доступа к полям

Можно изменить доступность полей, унаследованных из другой модели.

      class InheritedModel(models.Model):
      _inherit = 'existing.model'
      
          existing_field = fields.Char(string="Existing Field", readonly=True)

# Наследование нескольких моделей (multiple inheritance)

Этот способ используется для наследования нескольких моделей и объединения их функционала.

      class MultiInheritedModel(models.Model):
         _inherit = ['existing.model1', 'existing.model2']
         # Поля и методы из обеих моделей будут доступны здесь


      class StockLot(models.Model):
         # _inherit = 'stock.lot'
         _name = 'stock.lot'
         _inherit = ['stock.lot', 'mo_reports_sm_line_report.mixin_logger']

Когда вы используете _inherit с несколькими моделями в Odoo, это называется множественным наследованием. В этом случае
вы можете расширить функциональность существующей модели (stock.lot) и добавить новую функциональность из миксина (
mo_reports_sm_line_report.mixin_logger).


