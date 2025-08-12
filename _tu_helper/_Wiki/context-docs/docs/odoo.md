==========================
## odoo-model
==========================
Odoo - Backend - Модели
--------------------------------------------
Пример простой модели Odoo.

```python
from odoo import models, fields

class Book(models.Model):
    _name = "library.book"
    _description = "Book"
    name = fields.Char(required=True)
    author = fields.Char()
    published = fields.Date()
```
## odoo-view
Odoo - UI - Формы
Определение формы в XML.

```xml
<odoo>
  <record id="view_book_form" model="ir.ui.view">
    <field name="name">library.book.form</field>
    <field name="model">library.book</field>
    <field name="arch" type="xml">
      <form>
        <sheet>
          <group>
            <field name="name"/>
            <field name="author"/>
            <field name="published"/>
          </group>
        </sheet>
      </form>
    </field>
  </record>
</odoo>
```
