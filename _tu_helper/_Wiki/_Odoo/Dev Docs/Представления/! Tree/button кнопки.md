button кнопки
===================================================
   
      <tree default_order="sequence">
         <field name="sequence" widget="handle"/>
         <field name="name" optional="show"/>
         <field name="name1" optional="hide"/>
         <field name="state" optional="show" />
         <button string="New button" name="create" attrs="{'invisible': [('state','=','posted')]}"/>
      </tree>

У перегляді списком можна використовувати кнопки, вони будуть відображатись у стовпчиках аналогічно полям
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком9.png
   
      <tree default_order="sequence">
         <field name="sequence" widget="handle"/>
         <field name="name" optional="show"/>
         <field name="name1" optional="hide"/>
         <field name="state" optional="show" />
         <button icon="fa-ticket"  name="create" attrs="{'invisible': [('state','=','posted')]}"/>
      </tree>

Кнопка може використовувати іконку, що дозволяє економити місце
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком10.png