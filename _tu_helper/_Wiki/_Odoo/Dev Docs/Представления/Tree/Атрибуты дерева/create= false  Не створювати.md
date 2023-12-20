
create="false" Не створювати
===================================================

    <tree create="false">
       <field name="name"/>
       <field name="name1"/>
       <field name="state" widget="badge"
              decoration-success="state == 'posted'"
              decoration-info="state == 'draft'"/>
    </tree>

Атрибут create визначає чи буде відображатись кнопка Створити. Зв замовчуванню кнопка відображається

Приклад в _tu_helper\_Wiki\_Odoo\Pictures\Представлення списком2.png


    <tree create="0">
        <field name="date"/>
        <field name="account_id"/>