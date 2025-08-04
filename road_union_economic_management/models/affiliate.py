from odoo import models, fields, _


class Affiliate(models.Model):

    _inherit = 'affiliation.affiliate'

    payment_account_ids = fields.One2many(
        comodel_name="affiliate.payment_account",
        inverse_name="affiliate_id",
        string="Economic Movements"
    )
