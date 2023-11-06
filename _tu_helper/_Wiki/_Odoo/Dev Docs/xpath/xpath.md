    <xpath expr="//page[@id='invoice_tab']//tree" position="inside">

Подмена атрибутов form 
===============================================

    <xpath expr="//form" position="attributes">
        <attribute name="create">1</attribute>
        <attribute name="edit">1</attribute>
    </xpath>

Подмена атрибутов field
===============================================

    <xpath expr="//page[@id='invoice_tab']//tree//field[@name='price_subtotal']" position="attributes">
        <attribute name="sum">"Total price_subtotal"</attribute>
    </xpath>
