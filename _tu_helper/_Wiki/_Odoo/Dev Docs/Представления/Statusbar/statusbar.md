Создание selection-поля с виджетом statusbar в Odoo включает несколько шагов. 
Мы создадим новое поле, определим его как
selection и выведем на форму с использованием виджета statusbar. Также рассмотрим параметры, которые можно использовать
в виджете statusbar.


Определение модели и добавление selection-поля models/example_model.py
==============================
поле, определим его как selection

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string="Status", default='draft')

Создание представления формы с виджетом statusbar views/example_model_views.xml
==============================
# form view

    <record id="view_form_example_model" model="ir.ui.view">
        <field name="name">example.model.form</field>
        <field name="model">example.model</field>
        <field name="arch" type="xml">
            <form string="Example Model">
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,done" 
                            statusbar_colors='{"draft":"blue","confirmed":"orange","done":"green"}'/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

# Кликабельность поля
    <field name="stage_id" widget="statusbar" options="{'clickable': '1'}"

Поле state отображается с виджетом statusbar.
Атрибут statusbar_visible указывает, какие состояния видны в статусбаре.
Атрибут statusbar_colors задает цвета для различных состояний.


# tree view

    <record id="view_tree_example_model" model="ir.ui.view">
        <field name="name">example.model.tree</field>
        <field name="model">example.model</field>
        <field name="arch" type="xml">
            <tree string="Example Model">
                <field name="name"/>
                <field name="state" widget="statusbar"/>
            </tree>
        </field>
    </record>


Поле state также отображается с виджетом statusbar.
statusbar_visible: Определяет, какие состояния будут отображаться в статусбаре.

