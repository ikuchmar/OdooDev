<pivot> - виджет для отображения связанных записей в виде сводной таблицы.
Этот виджет подходит для анализа данных и вычисления агрегатных значений.

<field name="sales" widget="one2many_pivot">
    <pivot>
        <field name="product"/>
        <field name="quantity" type="measure" function="sum"/>
        <field name="price" type="measure" function="sum"/>
        <field name="date" interval="day"/>
    </pivot>
</field>