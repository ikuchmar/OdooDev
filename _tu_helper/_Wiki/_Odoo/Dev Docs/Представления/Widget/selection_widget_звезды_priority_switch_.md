звезды widget="priority"
===========================
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High'),
        ('2', 'Very High'),
        ('3', 'Critical')]
                                )

# form

![img.png](img.png)

    <form>
        <xpath expr="//field[@name='date_last_stage_update']" position="after">
            <field name="priority" widget="priority_switch"/>
        </xpath>
    </form>

# tree
    
    <tree>
        <field name="priority" widget="priority" nolabel="1"/>
    </tree>

# kanban
    <kanban> 
        <div class="o_kanban_record_bottom" t-if="!selection_mode">
            <div class="oe_kanban_bottom_left" t-att-class="['1_done', '1_canceled'].includes(record.state.raw_value) ? 'opacity-50' : ''">
                <field name="priority" widget="priority" style="margin-right: 5px;" field_id="priority_1"/>
    </kanban> 
