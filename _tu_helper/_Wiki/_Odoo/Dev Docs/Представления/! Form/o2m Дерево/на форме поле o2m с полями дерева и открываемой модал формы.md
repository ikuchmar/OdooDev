                       <notebook>
                            <page id="checks" string="Checks"
                                  groups="mo_vchasnokasa.group_mo_vchasnokasa_user">
                                <field name="check_ids">
                                #описание МОДАЛЬНОЙ формы записи
                                    <form>
                                        <header>
                                            <button name="print_check" string="Print" type="object"/>
                                            <button name="view_check" string="View" type="object"/>
                                        </header>
                                        <group>
                                            <group>
                                                <field name="create_date"/>
                                                <field name="account_move_id"/>
                                                <field name="check_type"/>
                                                <field name="pay_type"/>
                                                <field name="amount"/>
                                                <field name="fisn"/>
                                                <field name="report_url"/>
                                                <field name="qr"/>
                                                <field name="task"/>
                                                <field name="device_id"/>
                                            </group>
                                        </group>
                                    </form>
                                    #описание дерева поля o2m
                                    <tree>
                                        <field name="create_date" optional="show"/>
                                        <field name="account_move_id" optional="show"/>
                                        <field name="check_type" optional="show"/>
                                        <field name="pay_type" optional="show"/>
                                        <field name="amount" optional="show"/>
                                        <field name="fisn" optional="show"/>
                                        <field name="report_url" optional="show"/>
                                        <field name="qr" optional="show"/>
                                        <field name="task" optional="show"/>
                                        <field name="report_url"
                                               widget="url"
                                               class="fa fa-print"
                                               text="&#160;"
                                               nolabel="1"/>
                                        <field name="qr"
                                               widget="url"
                                               class="fa fa-search"
                                               text="&#160;"
                                               nolabel="1"/>
                                    </tree>
                                </field>
                            </page>


<field name="url2" widget="url" options="{'website_path': True}"/>
 <field name="url2" widget="url" options="{'website_path': True}"/>
 <field name="website" widget="url" placeholder="e.g. https://www.odoo.com"/>

  name="website" widget="url" options="{'url': 'https://www.example.com'}" />