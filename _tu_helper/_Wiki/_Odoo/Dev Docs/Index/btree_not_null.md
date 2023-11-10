index="btree_not_null"
===========================

    account_move_line_id = fields.Many2one('account.move.line', 'Invoice Line', readonly=True, check_company=True, index="btree_not_null")