    depreciation_move_ids = fields.One2many('account.move', 
                                            'asset_id', 
                                            string='Depreciation Lines', 
                                            readonly=True, 
                                            states={'draft': [('readonly', False)], 'open': [('readonly', False)], 'paused': [('readonly', False)]})
