Декорации в Odoo используются для изменения стиля записей в представлении дерева (tree view) на основе определенных
условий. 

Декорации могут изменять:
 -цвет текста, 
 - фона 
 - или применять другие стили для визуального выделения записей, соответствующих определенным критериям. 
 
Декорации задаются с помощью атрибутов decoration-* в представлении дерева.

Основные декорации

      decoration-bf: Полужирный текст (bold font).
      decoration-it: Курсивный текст (italic text).
      decoration-danger: Красный текст.
      decoration-warning: Оранжевый текст.
      decoration-info: Синий текст.
      decoration-muted: Серый текст.
      decoration-primary: Голубой текст.

Определение модели models/example_model.py
===============================================================
      
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
    ], string="Priority", default='1')

    active = fields.Boolean(string="Active", default=True)

представлении дерева (tree view)  views/example_model_views.xml
===============================================================

      <odoo>
         <record id="view_tree_example_model" model="ir.ui.view">
            <field name="name">example.model.tree</field>
            <field name="model">example.model</field>
            <field name="arch" type="xml">
               <tree string="Example Model"
                  decoration-danger="priority == '2'"
                  decoration-info="priority == '0'"
                  decoration-muted="not active">
               <field name="name"/>
               <field name="priority"/>
               <field name="active"/>
               </tree>
            </field>
         </record>
   
      </odoo>

Декорации:
decoration-danger="priority == '2'": Применяет красный цвет к записям с высокой приоритетностью (priority = 'High').
decoration-info="priority == '0'": Применяет синий цвет к записям с низкой приоритетностью (priority = 'Low').
decoration-muted="not active": Применяет серый цвет к неактивным записям (active = False).








