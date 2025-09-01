from odoo import models, fields, _


class Affiliate(models.Model):
    _inherit = 'affiliation.affiliate'

    payment_account_ids = fields.One2many(
        comodel_name="affiliate.payment_account",
        inverse_name="affiliate_id",
        string="Economic Movements"
    )

    id_benefit = fields.Integer(
        string='ID/BENEFIT',
        required=True,
    )

    _sql_constraints = [
        ('unique_id_benefit',
         'unique(id_benefit)',
         _('The ID/BENEFIT must be unique for each affiliate.'))
    ]
