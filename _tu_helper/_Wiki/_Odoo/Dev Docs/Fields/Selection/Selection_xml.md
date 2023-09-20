==========================
blacklisted_values
==========================

    <field name="program_type" widget="filterable_selection" 
                               attrs="{'readonly': [('coupon_count', '!=', 0)]}" 
                               options="{'blacklisted_values': ['gift_card', 'ewallet']}"/>