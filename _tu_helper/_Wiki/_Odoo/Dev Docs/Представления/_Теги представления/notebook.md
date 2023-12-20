notebook
===================================================
Тег notebook створює вкладки. Для створення окремої вкладки використовується тег page.
Розміщувати елементи на ній можна так само як і в середині сторінки, тобто використовуючи групи, поля, інші елементи та
методи.

    <notebook>
        <page id="dev_info" string="Dev info" groups='base.group_no_one'>

        </page>
    </notebook>


    <notebook>
       <page string="Authors">
           <field name="author_ids" mode="kanban"/>
       </page>
       <page string="Dates">
           <group>
               <field name="start_date"/>
               <field name="stop_date"/>
           </group>
       </page>
    </notebook>

Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення форми7.png
