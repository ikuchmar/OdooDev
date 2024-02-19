update *
Оновлює дані, має синтаксис, аналогічний write, але на відміну від write не записує у БД, а присвоює значення полям.

values.update({
   'acquirers': acquirers_sudo,
   'tokens': tokens,
   'fees_by_acquirer': fees_by_acquirer,
   'show_tokenize_input': logged_in,
   'amount': invoice.amount_residual,
   'currency': invoice.currency_id,
   'partner_id': partner_id,
   'access_token': access_token,
   'transaction_route': f'/invoice/transaction/{invoice.id}/',
   'landing_route': _build_url_w_params(
invoice.access_url, {'access_token': access_token})
})

Найчастіше використовується у методах с декоратором api.onchange