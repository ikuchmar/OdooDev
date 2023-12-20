    field_many2one_id = fields.Many2one(string='Many2one field',
                                        comodel_name='basic.fields',
                                        required=True,
                                        check_company=True,
                                        auto_join=True,
                                        ondelete='cascade')
