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


    <xpath expr="//button[@name='button_draft']" position="attributes">
        <attribute name="attrs">{'invisible' : [('show_reset_to_draft_button', '=', False), ('state', '=', 'verified')]}</attribute>
    </xpath>



    <xpath expr="//notebook//page[@name='order_lines']//field[@name='order_line']//tree//field[@name='product_template_id']"
           position="attributes">
        <attribute
                name="options">{'always_reload':True, 'no_create':True, 'no_quick_create':True, 'no_create_edit':True}</attribute>
    </xpath>

    <xpath expr="//notebook//page[@name='order_lines']//field[@name='order_line']//tree//field[@name='product_id']"
           position="attributes">
        <attribute
                name="options">{'always_reload':True, 'no_create':True, 'no_quick_create':True, 'no_create_edit':True}</attribute>
    </xpath>


Удалить атрибут editable
===============================================
xpath чтобы <tree string="Pricelist Rules" editable="bottom">  превратить в <tree string="Pricelist Rules">

    <xpath expr='//tree' position="attributes">
          <attribute name="editable"/>
    </xpath>


    <xpath expr="//notebook/page/group/group//field[@name='account_depreciation_id']" position="attributes">
        <attribute name="string">Deferred Revenue Account</attribute>
        <attribute name="help">Account used to record the deferred income</attribute>
        <attribute name="domain">[('account_type', '=', 'liability_current')]</attribute>
        <attribute name="context">{'default_account_type': 'liability_current', 'account_type_domain': [('account_type', '=', 'liability_current')]}</attribute>
    </xpath>


        <xpath expr="//field[@name='date']" position="after">
            <field name="warehouse_id"/>
        </xpath>


    <field name="original_move_line_ids" position="attributes">
        <attribute name="domain">[
            ('parent_state', '=', 'posted'),
            ('debit', '=', '0'),
            ('company_id', '=', company_id),
            ('account_id.account_type', '=', 'liability_current')
        ]</attribute>
    </field>

