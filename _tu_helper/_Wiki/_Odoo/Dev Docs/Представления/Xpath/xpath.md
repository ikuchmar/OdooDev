    <xpath expr="//page[@id='invoice_tab']//tree" position="inside">

Добавить Роль
==============================================
        <data>
            <xpath expr="//button[@name='button_validate'][1]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='button_validate'][2]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='action_toggle_is_locked'][1]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='action_toggle_is_locked'][2]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
        </data>

# Добавить поля в tree
==============================================
        <field name="arch" type="xml">
            <tree>
                <field name="id" optional="hide"/>
                <field name="temp_account_id" optional="hide"/>
                <field name="warehouse_id" optional="hide"/>
            </tree>
        </field>