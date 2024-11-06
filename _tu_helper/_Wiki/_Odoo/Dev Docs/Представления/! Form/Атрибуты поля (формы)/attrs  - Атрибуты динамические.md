invisible
==============================================

    <field name="date" attrs="{'invisible':[('property_valuation', '!=', 'real_time')]}"/>

readonly
==============================================

            <field name="city" position="attributes">
                <attribute name="attrs">
                    {'invisible': [('country_enforce_cities', '=', True), '|', ('city_id', '!=', False), ('city', 'in', ('',False))],
                     'readonly': [('type', '=', 'contact'), ('parent_id', '!=', False)]}
                </attribute>
            </field>

required
==============================================
			<xpath expr="//field[@name='registration_number']" position="attributes">
				<attribute name="attrs">{'required': [('cph', '!=', True)]}</attribute>
			</xpath>