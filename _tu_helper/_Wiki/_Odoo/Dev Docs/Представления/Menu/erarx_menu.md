<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- Top menu item -->
    <menuitem name="Invoicing"
        id="menu_finance"
        groups="account.group_account_readonly,account.group_account_invoice"
        web_icon="account,static/description/icon.png"
        sequence="55">
        <menuitem id="menu_finance_receivables" name="Customers" sequence="2">
            <menuitem id="menu_action_move_out_invoice_type" action="action_move_out_invoice_type" sequence="1"/>
            <menuitem id="menu_action_move_out_refund_type" action="action_move_out_refund_type" sequence="2"/>
            <menuitem id="menu_action_move_out_receipt_type" action="action_move_out_receipt_type" groups="account.group_sale_receipts" sequence="3"/>
            <menuitem id="menu_action_account_payments_receivable" action="action_account_payments" sequence="15"/>
            <menuitem id="product_product_menu_sellable" name="Products" action="product_product_action_sellable" sequence="100"/>
            <menuitem id="menu_account_customer" name="Customers" action="res_partner_action_customer" sequence="110"/>
        </menuitem>
        <menuitem id="menu_finance_payables" name="Vendors" sequence="3">
            <menuitem id="menu_action_move_in_invoice_type" action="action_move_in_invoice_type" sequence="1"/>
            <menuitem id="menu_action_move_in_refund_type" action="action_move_in_refund_type" sequence="2"/>
            <menuitem id="menu_action_move_in_receipt_type" action="action_move_in_receipt_type" groups="account.group_purchase_receipts" sequence="3"/>
            <menuitem id="menu_action_account_payments_payable" action="action_account_payments_payable" sequence="20"/>
            <menuitem id="product_product_menu_purchasable" name="Products" action="product_product_action_purchasable" sequence="100"/>
            <menuitem id="menu_account_supplier" name="Vendors" action="account.res_partner_action_supplier" sequence="200"/>
        </menuitem>
    </menuitem>
</odoo>