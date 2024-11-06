Создание кнопок, вызывающих действия (action), в Odoo может быть выполнено с использованием различных типов кнопок:
type="object" и type="action". Понимание разницы между этими типами кнопок важно для правильного использования и
функциональности в Odoo.

Разница между type="object" и type="action"
type="object": Кнопка вызывает метод Python, определенный в модели. Это позволяет выполнять любые действия, определенные
в этом методе, включая вызовы других методов, манипуляции с данными и выполнение бизнес-логики.

type="action": Кнопка вызывает заранее определенное действие (ir.actions.act_window). Это обычно используется для
открытия определенных представлений, таких как формы, деревья или канбан.


Определение модели и методов для кнопок - models/example_model.py
==============================

# Логика для кнопки типа object ('type': 'ir.actions.client',)

    def button_action_object(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Object Button Clicked',
                'message': 'You clicked the Object button!',
                'sticky': False,
            },
        }

# Логика для кнопки типа action ('type': 'ir.actions.act_window',)

    @api.model
    def button_action_open_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Example Models',
            'res_model': 'example.model',
            'view_mode': 'tree,form',
            'target': 'new',
        }

Создание представлений с кнопками views/example_model_views.xml
==============================

    <odoo>
        <record id="view_form_example_model" model="ir.ui.view">
            <field name="name">example.model.form</field>
            <field name="model">example.model</field>
            <field name="arch" type="xml">
                <form string="Example Model">
                    <sheet>
                        <group>
                            <field name="name"/>
                            <button name="button_action_object" string="Object Button" type="object" class="oe_highlight"/>
                            <button name="button_action_open_view" string="Action Button" type="action" class="oe_highlight"/>
                        </group>
                    </sheet>
                </form>
            </field>
        </record>
    
        <record id="view_tree_example_model" model="ir.ui.view">
            <field name="name">example.model.tree</field>
            <field name="model">example.model</field>
            <field name="arch" type="xml">
                <tree string="Example Model">
                    <field name="name"/>
                    <button name="button_action_object" string="Object Button" type="object" class="oe_highlight"/>
                    <button name="button_action_open_view" string="Action Button" type="action" class="oe_highlight"/>
                </tree>
            </field>
        </record>
    </odoo>

