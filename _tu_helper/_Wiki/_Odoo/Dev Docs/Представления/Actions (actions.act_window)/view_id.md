view_id:
=====================
Это идентификатор представления (view), который будет открыт при выполнении действия с видом в виде дерева (
tree view).


    <?xml version="1.0" encoding="utf-8"?>
    <odoo>
        <record id="mo_vchasnokasa_cron_action" model="ir.actions.act_window">
            <field name="name">Cron</field>
            <field name="res_model">ir.cron</field>
    
            # Указать внешний ID
            ================================
            <field name="view_id" ref="base.ir_cron_view_tree"/>
    
            <field name="view_mode">tree,form</field>
        </record>
    </odoo>