# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizards


def uninstall_hook(env):
    """ Delete `account.payment.method` records created for the installed payment providers. """
    installed_providers = env['payment.provider'].search([('module_id.state', '=', 'installed')])
    env['account.payment.method'].search([
        ('code', 'in', installed_providers.mapped('code')),
        ('payment_type', '=', 'inbound'),
    ]).unlink()
