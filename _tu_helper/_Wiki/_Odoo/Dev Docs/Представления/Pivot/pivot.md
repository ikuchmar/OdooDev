Определение Pivot View:

    <record id="view_pivot_your_model" model="ir.ui.view">
        <field name="name">your.model.pivot</field>
        <field name="model">your.model</field>
        <field name="arch" type="xml">
            <pivot string="Your Model Analysis">
                <!-- Определение измерений (measures) -->
                <field name="quantity" type="measure"/>
                <field name="price_total" type="measure"/>
    
                <!-- Определение группировок (dimensions) -->
                <field name="date" type="row"/>
                <field name="product_id" type="row"/>
                <field name="category_id" type="col"/>
            </pivot>
        </field>
    </record>

<pivot>: Главный тег для определения представления Pivot.
<field name="quantity" type="measure"/>: Определяет измерение, например, количество.
<field name="price_total" type="measure"/>: Еще одно измерение, например, общая цена.
<field name="date" type="row"/>: Группировка по дате (в строках).
<field name="product_id" type="row"/>: Группировка по продукту (в строках).
<field name="category_id" type="col"/>: Группировка по категории (в колонках).