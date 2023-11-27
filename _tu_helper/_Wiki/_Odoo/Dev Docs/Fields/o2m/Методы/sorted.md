sorted
====================================================
    for move in asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv._origin.id)):

        remaining -= move.depreciation_value
        depreciated += move.depreciation_value
        move.asset_remaining_value = remaining
        move.asset_depreciated_value = depreciated