invisible приховування
===================================================
    
    <tree default_order="sequence">
       <field name="sequence" widget="handle"/>
       <field name="name" optional="show"/>
       <field name="name1" optional="hide"/>
       <field name="state" optional="show" />
       <button icon="fa-ticket"  name="create" attrs="{'invisible': [('state','=','posted')]}"/>
    </tree>

При використанні приховування елемент (поле або кнопка) будуть приховані, але стовпчик залишеться, навіть, якщо всі значення будуть приховані
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком11.png
===================================================