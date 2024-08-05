sum (итоги)
=====================================

    <field name="your_field" sum="Total" widget="monetary" options="{'currency_field': 'currency_id'}"/>

Атрибут sum="Total" указывает, что нужно отобразить итоги для этого поля. 

Обратите внимание, что это будет работать для полей, которые поддерживают агрегацию и имеют подходящий тип (например, числовой или валютный).


    <field name="debit" sum="Total Debit" attrs="{'invisible': [('display_type', 'in', ('line_section', 'line_note'))], 'readonly': [('parent.move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')), ('display_type', 'in', ('line_section', 'line_note', 'product'))]}"/>
    <field name="credit" sum="Total Credit" attrs="{'invisible': [('display_type', 'in', ('line_section', 'line_note'))], 'readonly': [('parent.move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')), ('display_type', 'in', ('line_section', 'line_note', 'product'))]}"/>
