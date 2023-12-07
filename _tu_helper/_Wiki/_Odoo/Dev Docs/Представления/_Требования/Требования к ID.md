AssertionError: The ID reference "mo_stock.location.tree" must contain
maximum one dot. They are used to refer to other modules ID, in the
form: module.record_id

в record id - разрешается только одна "."
=================================================
<record id="mo_stock.location.tree"

# нужно так (типа того)
<record id="mo_stock_location.tree" 

    <?xml version="1.0" encoding="utf-8"?>
    <odoo>
    
        <record id="mo_stock.location.tree" model="ir.ui.view">
            <field name="name">mo_stock.location.tree</field>
            <field name="model">stock.location</field>
            <field name="inherit_id" ref="stock.view_location_tree2"/>
            <field name="arch" type="xml">
                <tree>
                    <field name="id"/>
                    <!--                <field name="temp_is_not_create_am" optional="hide" groups='base.group_no_one'/>-->
                </tree>
            </field>
        </record>
    </odoo>