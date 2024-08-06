В Odoo концепция _inherits используется для реализации наследования делегирования, которое позволяет одной модели
расширять другую модель путем создания ссылки на нее, а не через непосредственное наследование. Это позволяет модели
использовать поля и методы другой модели как свои собственные, сохраняя при этом отдельные таблицы в базе данных.

Основные концепции и преимущества _inherits
Делегированное наследование: Одна модель (дочерняя) ссылается на другую модель (родительскую) через внешний ключ. Поля
родительской модели становятся доступными в дочерней модели.
Разделение таблиц: В отличие от _inherit, где данные хранятся в одной таблице, _inherits поддерживает отдельные таблицы
для родительской и дочерней моделей.
Полная функциональность родительской модели: Дочерняя модель может использовать методы и поля родительской модели, как
если бы они были определены в ней самой.

Пример использования _inherits
Предположим, у нас есть базовая модель res.partner, и мы хотим создать модель res.student, которая использует все поля и
методы модели res.partner, а также добавляет свои собственные поля.

# Определение модели и добавление полей models/res_student.py

    class Student(models.Model):
        _name = 'res.student'
        _inherits = {'res.partner': 'partner_id'}
    
        partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
        student_number = fields.Char(string="Student Number")
        enrollment_date = fields.Date(string="Enrollment Date")

Модель res.student:
Использует делегированное наследование от res.partner через атрибут _inherits.

# Создание представлений views/res_student_views.xml

    <odoo>
        <record id="view_form_res_student" model="ir.ui.view">
            <field name="name">res.student.form</field>
            <field name="model">res.student</field>
            <field name="arch" type="xml">
                <form string="Student">
                    <sheet>
                        <group>
                            <field name="name"/>
                            <field name="student_number"/>
                            <field name="enrollment_date"/>
                            <field name="email"/>
                        </group>
                    </sheet>
                </form>
            </field>
        </record>

Отображает поля name (из модели res.partner), student_number, enrollment_date, и email (из модели res.partner).

        <record id="view_tree_res_student" model="ir.ui.view">
            <field name="name">res.student.tree</field>
            <field name="model">res.student</field>
            <field name="arch" type="xml">
                <tree string="Student">
                    <field name="name"/>
                    <field name="student_number"/>
                    <field name="enrollment_date"/>
                    <field name="email"/>
                </tree>
            </field>
        </record>
    </odoo>

Отображает поля name, student_number, enrollment_date, и email.

