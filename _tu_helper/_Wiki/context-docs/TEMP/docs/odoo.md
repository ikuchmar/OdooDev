## api-decorators
categories: ERP - Odoo - Python API
aliases: @api, decorators
Декораторы Odoo: @api.model, @api.depends, @api.constrains.
```python
@api.model
def create(self, vals):
    return super().create(vals)
```

---

## xml-views
categories: ERP - Odoo - Views
aliases: qweb, xml
Наследование и изменение QWeb/Views через XPath.
```xml
<xpath expr="//field[@name='name']" position="attributes">
  <attribute name="string">Название</attribute>
</xpath>
```
