
Сепаратор
===================================================

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <filter name="author_info" string="By Info author" domain="[('author_ids.name','ilike','info')]"/>
               <filter name="qty_gt_2" string="Greater then 2" domain="[('qty','>',2)]" />
               <separator/>
               <filter name="created_last_week" string="Last week" domain="[('create_date', '&gt;', (context_today() - relativedelta(weeks=1)).strftime('%Y-%m-%d') )]"/>
               <filter name="filter_create_date" date="create_date" string="Creation Date" default_period="last_month"/>
               <filter name="groupby_name" string="Name" context="{'group_by': 'name'}"/>
               <filter name="groupby_state" string="State" context="{'group_by': 'state'}"/>
           </search>
       </field>
    </record>
Тег separator створює лінію в меню, що дозволяє створити візуальне групування фільтрів. Це розділення є суто візуальним і ніяк не впливає на роботу.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку6.png
