edit="false"
============================
    <tree string="Journal Items" create="false" edit="true" expand="context.get('expand', False)" multi_edit="1" sample="1">

           <tree edit="false" create="false" delete="false">
                <field name="name"/>
                <field name="user_id"/>

edit="0"
============================
    <tree create="0">
        <field name="date"/>
        <field name="account_id"/>

edit: принимает значение true или false. Если установлено значение false, 
то ячейки со значениями в таблице будут заблокированы для редактирования;
