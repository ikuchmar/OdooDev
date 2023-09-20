<form> - виджет для отображения связанных записей в виде формы. Этот виджет подходит для отображения связанных записей внутри формы родительской записи.
Пример использования:


<field name="orders" widget="one2many_form">
    <form>
        <sheet>
            <group>
                <field name="order_number"/>
                <field name="order_date"/>
                <field name="customer"/>
            </group>
        </sheet>
    </form>
</field>
