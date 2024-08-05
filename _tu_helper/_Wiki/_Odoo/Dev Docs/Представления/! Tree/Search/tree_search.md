тега <search>:
====================================================
Загальний вигляд представлення

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <field name="name"/>
           </search>
       </field>
    </record>

Для створення представлення пошуку створюється запис в моделі ir.ui.view для потрібної моделі та в поле arch додається
xml опис даного представлення.
Весь контент має бути огорнутий у тег search, а в ньому іде опис полів, фільтрів, групувань, пошукова панель.

Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку1.png

==================================================
Пошук по полю (field)
Порядок полів для пошуку в стандартному поле search
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку2.png
===================================================

        <record id="kw_lib_book_search" model="ir.ui.view">
           <field name="name">kw.lib.book.search (kw_library)</field>
           <field name="model">kw.lib.book</field>
           <field name="arch" type="xml">
               <search>
                   <field name="name" filter_domain="['|',('state','ilike',self),('name','ilike',self)]"/>
                   <field name="qty" operator=">"/>
                   <field name="state"/>
                   <field name="author_ids" domain="[('name','ilike','info')]"/>
               </search>
           </field>
        </record>

Пошук по полю автоматично запускається, коли користувач починає набирати в елементі пошуку, пропозиції пошуку будуть
відображатись у порядку, визначеному в xml.


Поиск по имени:
===============================

    <record model="ir.ui.view" id="view_name_search">
      <field name="name">Name Search</field>
      <field name="model">res.partner</field>
      <field name="arch" type="xml">
        <search>
          <field name="name"/>
        </search>
      </field>
    </record>

---------------------------------------------------
оператор OR:
---------------------------------------------------

    <record model="ir.ui.view" id="view_name_email_search">
      <field name="name">Name and Email Search</field>
      <field name="model">res.partner</field>
      <field name="arch" type="xml">
        <search>
          <field name="name"/>
          <field name="email"/>
          <operator string="OR"/>
        </search>
      </field>
    </record>

Встановлений фільтр (filter)
=====================================================
Фільтр, на відміну від поля, не використовує введене значення, а використовує попередньо встановлені умови. Для цього є
атрибут domain,
який може використовувати контекстні змінні та функції, наприклад функції роботи з датою context_today або
relativedelta.

Використувуеться filter а не field

    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <filter name="qty_gt_2" string="Greater then 2" domain="[('qty','>',2)]"/>
               <filter name="author_info" string="By Info author" domain="[('author_ids.name','ilike','info')]"/>
               <filter name="created_last_week" string="Last week" domain="[('create_date', '&gt;', (context_today() - relativedelta(weeks=1)).strftime('%Y-%m-%d') )]"/>
           </search>
       </field>
    </record>


Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку3.png

---------------------------------------------------
Специфіка для дат
---------------------------------------------------
Поиск по дате истечения срока действия контракта:

    <record model="ir.ui.view" id="view_contract_expiry_search">
      <field name="name">Contract Expiry Search</field>
      <field name="model">account.analytic.account</field>
      <field name="arch" type="xml">
        <search>
          <field name="date"/>
          <field name="date_expiry"/>
          <filter name="expiry" string="Expiry Soon">
            ['|', ('date_expiry', '<=', (context_today() + relativedelta(days=15)).strftime('%Y-%m-%d')), ('date_expiry', '=', False)]
          </filter>
        </search>
      </field>
    </record>
    
    
    <record id="kw_lib_book_search" model="ir.ui.view">
       <field name="name">kw.lib.book.search (kw_library)</field>
       <field name="model">kw.lib.book</field>
       <field name="arch" type="xml">
           <search>
               <filter name="filter_create_date" date="create_date" string="Creation Date"/>
           </search>
       </field>
    </record>

Поля типу Date або Datetime без вказаного домену мають специфічний фільтр, який дозволяє обрати один з трьох найближчих
місяціі, кварталів, років.
Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення пошуку4.png


---------------------------------------------------
оператор "ilike". фильтрацию по подстроке, то есть ищет все записи, в которых значение поля содержит указанную строку.
---------------------------------------------------

    <record model="ir.ui.view" id="view_name_contains_search">
      <field name="name">Name Contains Search</field>
      <field name="model">res.partner</field>
      <field name="arch" type="xml">
        <search>
          <field name="name" operator="ilike"/>
        </search>
      </field>
    </record>

---------------------------------------------------
"заполнен"  "!=". Этот оператор выполняет фильтрацию по отсутствию пустого значения в поле, то есть ищет все записи, в которых значение поля не равно пустому значению.
---------------------------------------------------

    <record model="ir.ui.view" id="view_email_not_empty_search">
      <field name="name">Email Not Empty Search</field>
      <field name="model">res.partner</field>
      <field name="arch" type="xml">
        <search>
          <field name="email" operator="!="/>
        </search>
      </field>
    </record>

===================================================
=

Важливо! Якщо явно не вказаний атрибут operator чи filter_domain, 
для числових полів буде використовуватись оператор
рівності, що еквівалентно

[('qty','=',self)]

а строковим полям буде

[('name','ilike',self)]

Атрибут operator дозволяє змінити цю поведінку, поставити оператор більше для числових полів, рівність для строкових
тощо.

Атрибут filter_domain дозволяє створити складний домен, що може включати декілька полів та складні умови.

Важливо! Для цього домену значення пошуку містить зміна self

Атрибут domain працює для полів, що мають вибір (Many2one, Many2many тощо). Такий домен може використовувати контекстні
змінні, такі як uid.
