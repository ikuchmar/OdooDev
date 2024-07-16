# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards


def post_init_hook(env):
    """ Create `account.payment.method` records for the installed payment providers. """
    PaymentProvider = env['payment.provider']
    installed_providers = PaymentProvider.search([('module_id.state', '=', 'installed')])
    for code in set(installed_providers.mapped('code')):
        PaymentProvider._setup_payment_method(code)


