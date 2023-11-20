"no_open": True
=================================

    <field name="vchasnokasa_device_id" options="{'no_open': True}"/>

"no_quick_create": True
=================================

	<field name="second_state_id" class="o_address_state" placeholder="State"
						   options="{'no_open': True, 'no_quick_create': True}"

"no_create": True
=================================

    <field name="second_country_id" placeholder="Country" class="o_address_country"
						   options='{"no_open": True, "no_create": True}'

{'no_create_edit': True}: Предотвращает создание и редактирование записей для поля Many2one.
=================================

    <field name="partner_id" options="{'no_create_edit': True}" />

{'no_open': True}: Предотвращает открытие формы связанной записи при клике на поле.
=================================

    <field name="related_partner_id" options="{'no_open': True}" />

{'no_quick_create': True}: Предотвращает быстрое создание записей для поля Many2one.
=================================

    <field name="category_id" options="{'no_quick_create': True}" />

{'widget': 'handle'}:
=================================

    Включает обработку, что позволяет пользователю легко изменять порядок записей в поле Many2many.

    <field name="product_ids" options="{'widget': 'handle'}" />

{'readonly': True}: Устанавливает поле в режим "только для чтения", делая его недоступным для редактирования.
=================================

    <field name="field_name" options="{'readonly': True}" />

Эти примеры предоставляют общее представление о том, как можно использовать опции. Однако конкретные опции и их влияние
могут зависеть от контекста и используемого виджета. Документация к Odoo и комментарии в исходном коде могут
предоставить более точные сведения о доступных опциях для конкретного поля или виджета.