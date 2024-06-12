Чтобы ограничить возможность создания записей напрямую из поля типа many2one (многие к одному), нужно использовать
параметр options="{'no_create': True}" в определении поля во views. Это ограничение будет применено к полю many2one, и
пользователи смогут только выбирать существующие записи, но не создавать новые из выпадающего списка.

Пример реализации
Модель
Предположим, что у вас есть модель sale.order, и вы хотите ограничить поле product_id, чтобы пользователь мог только
выбирать существующие продукты.

XML представление
В представлении формы добавьте параметр options="{'no_create': True}" к полю product_id.

Пример views/sale_order_views.xml
xml
Копировать код
<odoo>
<record id="view_order_form" model="ir.ui.view">
<field name="name">sale.order.form</field>
<field name="model">sale.order</field>
<field name="arch" type="xml">
<form string="Sales Order">
<sheet>
<group>
<field name="partner_id"/>
<field name="order_line">
<tree editable="bottom">
<field name="product_id" options="{'no_create': True}"/>
<field name="product_uom_qty"/>
<field name="price_unit"/>
</tree>
</field>
</group>
</sheet>
</form>
</field>
</record>
</odoo>
Полный пример модуля
Структура модуля
markdown
Копировать код
no_create_product/
├── __init__.py
├── __manifest__.py
├── models/
│ ├── __init__.py
│ ├── sale_order.py
├── views/
│ ├── sale_order_views.xml
__manifest__.py
python
Копировать код
{
'name': 'No Create Product',
'version': '1.0',
'category': 'Sales',
'summary': 'Restrict creation of new products from sale order form',
'description': """
This module restricts the creation of new products directly from the sale order form.
""",
'author': 'Your Name',
'depends': ['sale'],
'data': [
'views/sale_order_views.xml',
],
'installable': True,
'auto_install': False,
}
models/__init__.py
python
Копировать код
from . import sale_order
models/sale_order.py
python
Копировать код
from odoo import models, fields

class SaleOrder(models.Model):
_inherit = 'sale.order'
views/sale_order_views.xml
xml
Копировать код
<odoo>
<record id="view_order_form" model="ir.ui.view">
<field name="name">sale.order.form</field>
<field name="model">sale.order</field>
<field name="arch" type="xml">
<form string="Sales Order">
<sheet>
<group>
<field name="partner_id"/>
<field name="order_line">
<tree editable="bottom">
<field name="product_id" options="{'no_create': True}"/>
<field name="product_uom_qty"/>
<field name="price_unit"/>
</tree>
</field>
</group>
</sheet>
</form>
</field>
</record>
</odoo>
Заключение
Добавление параметра options="{'no_create': True}" к полю many2one в представлении формы позволит ограничить создание
новых записей, обеспечивая, что пользователи могут выбирать только из существующих записей. Этот метод применяется во
многих сценариях, где требуется строгий контроль над вводом данных.