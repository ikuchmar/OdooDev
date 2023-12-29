Панель пошуку
===================================================

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <searchpanel view_types="tree,pivot">
                   <field name="state"/>
               </searchpanel>
           </search>
       </field>
    </record>

Панель пошуку - швидкий інструмент для фільтрації даних, створюється за допомогою тегу searchpanel і доступний для представлень з багатьма записами,
 такими як список, канбан тощо і відповідно недоступний для форми і аналогічних представлень.
 За замовчанням відкритий для представлень список та канбан, але може бути відкритим до інших представлень за допомогою атрибута view_types, де через кому перелічуються потрібні представлення.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку7.png

Іконка
===================================================

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <searchpanel view_types="tree,pivot">
                   <field name="state" icon="fa-ticket" color="red"/>
               </searchpanel>
           </search>
       </field>
    </record>

Атрибут icon для тегу поля дозволяє замінити іконку за замовчанням, а атрибут color замінити її колір.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку8.png

Множинний вибір
===================================================


    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <searchpanel view_types="tree,pivot">
                   <field name="state" select="multi" enable_counters="1"/>
               </searchpanel>
           </search>
       </field>
    </record>


За допомогою атрибута select можна переключати одиничний вибір one чи множинний multi.
За допомогою атрибуту enable_counters можна додати обчислення кількості записів, які відповідають
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку9.png

Ієрархія
===================================================

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <searchpanel view_types="tree,pivot">
                   <field name="category_id" hierarchize="1" enable_counters="1"/>
                   <field name="state" select="one" enable_counters="1"/>
               </searchpanel>
           </search>
       </field>
    </record>

За допомогою атрибута hierarchize для Many2one полів, що посилаються на ієрархічну модель можна переключати відображення у вигляді дерева.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку10.png
