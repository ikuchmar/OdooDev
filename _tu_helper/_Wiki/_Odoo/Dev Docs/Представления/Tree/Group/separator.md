separator
=========================================================

       <record id="sorted_pricelist_search" model="ir.ui.view">
            <field name="name">mo_product.pricelist.search</field>
            <field name="model">product.pricelist.item</field>
            <field name="arch" type="xml">
                <search string="Products">
                    <field name="name"/>

                    <separator/>

                    <group expand='0' string='Group by'>
                        <filter string='Vendor' name="group_by_vendor_id"
                                context="{'group_by': 'vendor_id'}"/>
                        <filter string='Agreement' name="group_by_agreement_id"
                                context="{'group_by': 'purchase_requisition'}"/>
                        <filter string='Pricelist' name="group_by_pricelist_id"
                                context="{'group_by': 'pricelist_id'}"/>
                    </group>
                </search>
            </field>
        </record>

