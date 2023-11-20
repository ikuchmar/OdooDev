id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_first_model_base_group_user,first_model base_group_user,first_module.model_first_model,base.group_user,1,1,1,1
При этом, эту запись вы можете указать и в виде xml файла:


<record id="access_first_model_base_group_user" model="ir.model.access">
    <field name="name">first_model base_group_user</field>
    <field name="model_id" ref="first_module.model_first_model"/>
    <field name="group_id" ref="base.group_user"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>