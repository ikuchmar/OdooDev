# Наследование существующего представления (view)

Этот способ используется для добавления новых полей или виджетов к существующему представлению модели.

      <odoo>
         <record id="view_inherited_form" model="ir.ui.view">
            <field name="name">existing.model.form.inherited</field>
            <field name="model">existing.model</field>
            <field name="inherit_id" ref="existing_module.view_existing_model_form"/>
            <field name="arch" type="xml">
               <xpath expr="//field[@name='field_name']" position="after">
               <field name="new_field"/>
               </xpath>
            </field>
         </record>
      </odoo>




