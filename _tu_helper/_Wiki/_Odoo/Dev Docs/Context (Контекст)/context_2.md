    # ======================================================
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        # Передаем аргументы поиска в контекст
        context = self.env.context.copy()
        
        context['search_domain'] = args
        start_date, finish_date = _find_date_domen(args)
        context['start_date'] = start_date
        context['finish_date'] = finish_date

        self = self.with_context(context)
        return super(SmLineReport, self).search(args, offset, limit, order, count)

        # Используем данные из контекста для фильтрации