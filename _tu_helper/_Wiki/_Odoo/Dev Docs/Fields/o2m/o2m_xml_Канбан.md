<kanban> - виджет для отображения записей в виде карточек, как в Kanban-доске. Этот виджет подходит для отображения связанных записей с дополнительными полями и статусами.
Пример использования:

<field name="tasks" widget="one2many_kanban">
    <kanban>
        <field name="name"/>
        <field name="description"/>
        <field name="status"/>
        <field name="priority"/>
    </kanban>
</field>
