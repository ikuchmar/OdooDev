?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <record id="view_move_form" model="ir.ui.view">
            <field name="name">account.move.form.sales_check</field>
            <field name="model">account.move</field>
            <field name="inherit_id" ref="account.view_move_form"/>
            <field name="arch" type="xml">
                <xpath expr="//notebook" position="inside">
                    <page id="vchasnokasa" string="Vchasno Kasa"
                          attrs="{'invisible': [('move_type', 'not in', ['out_invoice', 'out_refund'])]}">
                        <header>

                            <button name="sales_check" string="Sales Check" type="object"
                                    confirm="Are you sure you want to register a sales receipt?"/>

                            <button name="return_check" string="Return Check" type="object"
                                    confirm="Are you sure you want to register a return check?"/>

