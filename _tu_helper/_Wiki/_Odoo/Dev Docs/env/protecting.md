   # make sure to protect all the records being assigned, because the
   # assignments invoke method write() on non-protected records, which may
   # cause an infinite recursion in case method write() needs to read one
   # of these fields (like in case of a base automation)

   fields = [type(self).asset_remaining_value, type(self).asset_depreciated_value]

   with self.env.protecting(fields, self.asset_id.depreciation_move_ids):

       for asset in self.asset_id:
           depreciated = 0
           remaining = asset.total_depreciable_value - asset.already_depreciated_amount_import
           for move in asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv._origin.id)):
               remaining -= move.depreciation_value
               depreciated += move.depreciation_value
               move.asset_remaining_value = remaining
               move.asset_depreciated_value = depreciated
