<tree string="Analytic Accounts" multi_edit="1">
                    <field name="company_id" invisible="1"/>
                    <field name="name" string="Name"/>
                    <field name="code"/>
                    <field name="partner_id"/>
                    <field name="plan_id"/>
                    <field name="active" invisible="1"/>
                    <field name="company_id" groups="base.group_multi_company"/>
                    <field name="debit" sum="Debit"/>
                    <field name="credit" sum="Credit"/>
                    <field name="balance" sum="Balance"/>
                </tree>