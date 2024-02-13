    <button name="action_time_off_dashboard" 
            type="object" 
            class="oe_stat_button" 
            icon="fa-calendar" 
            context="{'search_default_employee_ids': active_id}" 
            help="Залишок відпусток" 
            modifiers="{&quot;invisible&quot;: [[&quot;show_leaves&quot;, &quot;=&quot;, false]]}">
        
        <div class="o_field_widget o_stat_info" modifiers="{&quot;invisible&quot;: [[&quot;allocation_display&quot;, &quot;=&quot;, &quot;0&quot;]]}">
            <span class="o_stat_value">
                <field name="allocation_remaining_display" modifiers="{&quot;readonly&quot;: true}"/>/<field name="allocation_display" modifiers="{&quot;readonly&quot;: true}"/> Дні
            </span>
            <span class="o_stat_text">
                Відпустка
            </span>
        </div> 

        <div class="o_field_widget o_stat_info" modifiers="{&quot;invisible&quot;: [[&quot;allocation_display&quot;, &quot;!=&quot;, &quot;0&quot;]]}">
            <span class="o_stat_text">
               Відпустка
            </span>
        </div>
    </button>


    <button class="oe_stat_button" type="action" name="596" icon="fa-calendar">
        <div class="o_stat_info">
            <span class="o_stat_text">Табелі</span>
        </div>
    </button>