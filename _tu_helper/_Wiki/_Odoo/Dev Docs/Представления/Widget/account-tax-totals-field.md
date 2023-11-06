# 
==========================================================

    <field name="tax_totals" widget="account-tax-totals-field" nolabel="1" colspan="2" attrs="{'readonly': ['|', ('state', '!=', 'draft'), '&amp;', ('move_type', 'not in', ('in_invoice', 'in_refund', 'in_receipt')), ('quick_edit_mode', '=', False)]}"/>

 