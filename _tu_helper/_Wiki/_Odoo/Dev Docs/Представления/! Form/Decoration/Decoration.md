Декорации (decorations) в форме (form view) используются для изменения стиля полей или групп полей на основе
определенных условий. 
Это позволяет визуально выделять поля, которые соответствуют определенным критериям, например,
изменять их цвет, делать их полужирными или зачеркивать. 

Основные виды декораций для form view:

    decoration-bf: Полужирный текст (bold font).
    decoration-it: Курсивный текст (italic text).
    decoration-danger: Красный текст.
    decoration-warning: Оранжевый текст.
    decoration-info: Синий текст.
    decoration-muted: Серый текст.
    decoration-primary: Голубой текст.

Декорации применяются через атрибуты XML в определении формы, могут быть применены как:
- к отдельным полям, 
- так и к группам полей. 


Определение модели
==============================

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
    ], string="Priority", default='1')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string="Status", default='draft')
    active = fields.Boolean(string="Active", default=True)

Создание представлений views/example_model_views.xml
==============================

    <odoo>
        <record id="view_form_example_model" model="ir.ui.view">
            <field name="name">example.model.form</field>
            <field name="model">example.model</field>
            <field name="arch" type="xml">
                <form string="Example Model">
                    <sheet>
                        <group>
                            <field name="name" decoration-danger="priority == '2'" decoration-info="priority == '0'"/>
                            <field name="priority"/>
                        </group>
                        <group string="Status Information" decoration-muted="status == 'draft'">
                            <field name="status" decoration-bf="status == 'done'" decoration-it="status == 'draft'"/>
                            <field name="active"/>
                        </group>
                    </sheet>
                </form>
            </field>
        </record>
    </odoo>

Поле name с декорацией:
decoration-danger="priority == '2'": Применяет красный цвет, если приоритет высокий (priority = 'High').
decoration-info="priority == '0'": Применяет синий цвет, если приоритет низкий (priority = 'Low').

Поле status с декорацией:
decoration-bf="status == 'done'": Применяет полужирный текст, если статус "done".
decoration-it="status == 'draft'": Применяет курсивный текст, если статус "draft".

Группа Status Information с декорацией:
decoration-muted="status == 'draft'": Применяет серый цвет к группе, если статус "draft".
