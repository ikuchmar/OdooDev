search_view_id
===============================
Это идентификатор представления поиска, которое будет использоваться для поиска записей.

    <record id="action_move_in_refund_type" model="ir.actions.act_window">
        <field name="name">Refunds</field>
        <field name="res_model">account.move</field>
        <field name="view_mode">tree,kanban,form</field>
        <field name="view_id" ref="view_in_invoice_refund_tree"/>

        <field name="search_view_id" ref="view_account_invoice_filter"/>

        <field name="domain">[('move_type', '=', 'in_refund')]</field>
        <field name="context">{'default_move_type': 'in_refund'}</field>
        <field name="help" type="html">
          <p class="o_view_nocontent_smiling_face">
            Create a vendor credit note
          </p><p>
            Note that the easiest way to create a vendor credit note is to do it directly from the vendor bill.
          </p>
        </field>
    </record>