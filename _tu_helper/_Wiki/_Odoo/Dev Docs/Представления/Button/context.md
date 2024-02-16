context
========================

    <div class="oe_button_box" name="button_box">
        <button class="oe_stat_button"
            name="%(product_template_action_all)d"
            icon="fa-th-list"
            type="action"
            context="{'search_default_categ_id': active_id, 'default_categ_id': active_id, 'group_expand': True}">
            <div class="o_field_widget o_stat_info">
                <span class="o_stat_value"><field name="product_count"/></span>
                <span class="o_stat_text"> Products</span>
            </div>
        </button>
    </div>