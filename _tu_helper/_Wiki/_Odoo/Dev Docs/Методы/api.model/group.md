    # ======================================================
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        context = self.env.context.copy()

        context['search_domain'] = domain
        start_date, end_date = _find_date_domen(domain)
        context['start_date'] = start_date
        context['end_date'] = end_date

        self = self.with_context(context)

        # Вызов оригинального метода read_group
        return super(SmLineReport, self).read_group(domain, fields, groupby, offset, limit, orderby, lazy)


