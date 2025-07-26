установить группировку, которую нельзя снять
==============================================================================
<field name="context">{'group_by': ['channel_group_id']}</field>
==============================================================================

    <record id="website_slides.slide_channel_action_overview" model="ir.actions.act_window">
            <field name="name">All Courses</field>
            <field name="path">e-learning</field>
            <field name="res_model">slide.channel</field>
            <field name="view_mode">kanban,list,form</field>
            <field name="view_id" ref="website_slides.slide_channel_view_kanban"/>
            <field name="context">{'group_by': ['channel_group_id']}</field>
            <field name="help" type="html">
                <p class="o_view_nocontent_smiling_face">
                    <strong>Create a course</strong>
                </p>
                <p>
                    Your eLearning platform starts here!
                    <br/>
                    Upload content, set up rewards, manage attendees...
                </p>
            </field>
        </record>

установить группировку, которую МОЖНО снять
==============================================================================
<field name="is_default">1</field>
==============================================================================

        <record id="slide_channel_action_filter" model="ir.filters">
            <field name="name">Channel Group</field>
            <field name="model_id">slide.channel</field>
            <field name="user_id" eval="False"/>
            <!--                <field name="domain">[('shop_id', '!=', False)]</field>-->
            <field name="is_default">1</field>
            <field name="context">{'group_by': ['channel_group_id']}</field>
            <field name="action_id" ref="website_slides.slide_channel_action_overview"/>
        </record>