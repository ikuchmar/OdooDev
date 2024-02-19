@api.model
==========================================================
декоратор вказує, що метод відноситься до методів моделі, тобто параметр self не містить записів

    @api.model
    def _action_open_all_projects(self):
       action = self.env['ir.actions.act_window']._for_xml_id(
           'project.open_view_project_all' if not self.user_has_groups(
    'project.group_project_stages') else
           'project.open_view_project_all_group_stage')
       return action
