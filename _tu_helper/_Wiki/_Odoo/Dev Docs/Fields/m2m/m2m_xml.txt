========================================================
widget="many2many_tags"

Простое поле many2many в форме с использованием диалогового окна выбора значений:
========================================================
<field name="partner_ids" widget="many2many_tags"/>


========================================================
widget="many2many_tags"

Поле many2many с кастомной моделью связи:
в качестве представлений для добавления, редактирования и поиска записей
используются соответствующие tree, form и search представления.
========================================================
<field name="product_ids" widget="many2many_tags">
    <tree string="Products" editable="bottom">
        <field name="name"/>
        <field name="default_code"/>
        <field name="list_price"/>
    </tree>
    <form>
        <field name="name"/>
        <field name="default_code"/>
        <field name="list_price"/>
    </form>
    <search>
        <field name="name"/>
        <field name="default_code"/>
    </search>
</field>


========================================================
widget="many2many_checkboxes"

диалоговое окно с чекбоксами,
а для отображения значений используется tree представление с полями name и email.
========================================================
<field name="partner_ids" widget="many2many_checkboxes">
    <tree>
        <field name="name"/>
        <field name="email"/>
    </tree>
</field>

==================
отображает все значения из списка в виде чекбоксов,
которые можно выбирать для установки связи между объектами.


<field name="partner_ids" widget="many2many_checkboxes"/>


===========================================
виджет "many2many_tags".
выбирать несколько значений из списка, который появляется при вводе символов в поле.
===========================================
<field name="product_ids" widget="many2many_tags"/>


===========================================
checkboxes


===========================================
Many2many в виде дерева (tree):
===========================================
<field name="m2m_field" widget="many2many_tags">
    <tree string="Many2many Field">
        <field name="name"/>
        <field name="description"/>
    </tree>
</field>
===========================================
Many2many в виде списка (list):
===========================================
<field name="m2m_field" widget="many2many_list">
    <tree string="Many2many Field">
        <field name="name"/>
        <field name="description"/>
    </tree>
</field>
===========================================
Many2many в виде выпадающего списка (selection):
===========================================
<field name="m2m_field" widget="many2many_tags">
    <form>
        <sheet>
            <group>
                <field name="m2m_field"/>
            </group>
        </sheet>
    </form>
</field>
===========================================
Many2many с возможностью поиска и выбора нескольких значений:
===========================================
<field name="m2m_field" widget="many2many_tags">
    <form>
        <sheet>
            <group>
                <field name="m2m_field" widget="many2many_tags"/>
            </group>
        </sheet>
    </form>
</field>
===========================================
Many2many в виде календаря:
===========================================
<field name="m2m_field" widget="many2many_calendar">
    <calendar string="Many2many Field" date_start="date_field" date_stop="date_field">
        <field name="name"/>
        <field name="description"/>
    </calendar>
</field>