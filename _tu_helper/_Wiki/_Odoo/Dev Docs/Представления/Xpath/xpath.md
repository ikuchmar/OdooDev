    <xpath expr="//page[@id='invoice_tab']//tree" position="inside">

Добавить Роль
==============================================
        <data>
            <xpath expr="//button[@name='button_validate'][1]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='button_validate'][2]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='action_toggle_is_locked'][1]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
            <xpath expr="//button[@name='action_toggle_is_locked'][2]" position="attributes">
                <attribute name="groups" add="darkstore_role.group_darkstore"/>
            </xpath>
        </data>

Добавить поля в tree
==============================================
        <field name="arch" type="xml">
            <tree>
                <field name="id" optional="hide"/>
                <field name="temp_account_id" optional="hide"/>
                <field name="warehouse_id" optional="hide"/>
            </tree>
        </field>

Добавить поля с цветом 
==============================================
       <xpath expr="//field[@name='milestone_id']" position="after">
             <field name="assignee_id" style="color: green;"/>
        </xpath>


            <xpath expr="//field[@name='milestone_id']" position="after">
<!--                <field name="assignee_id" attrs="{'style': 'color: green;'}"/>-->
<!--                <field name="assignee_id" decoration-bf="2"/>-->
                <field name="assignee_id" style="background-color: green; color: white;"/>
            </xpath>

Добавить поля жирное 
==============================================
            <xpath expr="//field[@name='milestone_id']" position="after">
                <field name="assignee_id" style="font-weight: bold;"/>
            </xpath>


Свойство	Описание	Пример
color	Цвет текста	color: red;
background-color	Цвет фона	background-color: yellow;
font-weight	Жирный текст	font-weight: bold;
font-style	Курсив	font-style: italic;
text-decoration	Подчеркивание/зачеркивание	text-decoration: underline;
font-size	Размер шрифта	font-size: 14px;
text-align	Выравнивание текста (left, center, right)	text-align: center;
border	Граница вокруг элемента	border: 1px solid black;
border-radius	Скругление углов	border-radius: 10px;
padding	Внутренние отступы	padding: 5px;
margin	Внешние отступы	margin: 10px;
display	Отображение элемента (block, inline)	display: block;
visibility	Видимость (visible, hidden)	visibility: hidden;
opacity	Прозрачность (0 - полностью прозрачный)	opacity: 0.5;
cursor	Вид курсора (pointer, default)	cursor: pointer;
white-space	Перенос строк (nowrap, normal, pre-wrap)	white-space: nowrap;