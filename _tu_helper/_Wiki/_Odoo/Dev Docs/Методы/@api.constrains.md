
@api.constrains
==========================================================
Використовується для перевірки правильності введених даних.
Є альтернативою до _sql_constraints, але не діє на рівні СУБД і може бути проігнорований

    @api.constrains('vat', 'country_id')
    def check_vat(self):
       for partner in self:
           country = partner.commercial_partner_id.country_id
           if partner.vat and self._run_vat_test(partner.vat, country) is False:
               partner_label = _("partner [%s]", partner.name)
               msg = partner._build_vat_error_message(
                    country and country.code.lower() or None, partner.vat, partner_label)
               raise ValidationError(msg)

Важливо, таке обмеження спрацьовує лише за умови, якщо в вказані поля передаються значення.
Тобто у викликах create або write ці поля є в переліку.
