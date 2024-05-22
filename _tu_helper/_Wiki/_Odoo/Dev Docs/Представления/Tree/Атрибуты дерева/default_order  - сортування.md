
default_order  - сортування
===================================================

    <tree default_order="name">
    
       <field name="name" optional="show"/>
       <field name="name1" optional="hide"/>
       <field name="state" optional="show"/>
    </tree>
    
    Атрибут default_order надає можливість змінити сортування значень
    Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком7.png
    
    
    
    default_order="date asc, id asc" editable="top">
    
    <tree string="Move Lines" create="0" default_order="id desc" action="action_open_reference" type="object">