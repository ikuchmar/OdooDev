Групування
===================================================
context="{'group_by': 'name'}"
===================================================

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <filter name="groupby_name" 
                        string="Name" 
                        context="{'group_by': 'name'}"/>

               <filter name="groupby_state" string="State" context="{'group_by': 'state'}"/>
           </search>
       </field>
    </record>

За допомогою ключа group_by в атрибуті context фільтр створює в меню “Групувати за” групування за обраним полем.
Прийнято починати назву такого фільтру з префіксу groupby_
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку5.png
