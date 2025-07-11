from odoo import models, fields, _

class Affiliate(models.Model):

    _inherit = 'affiliation.affiliate'

    category = fields.Integer(string = 'Class')

    insurance_id = fields.Many2one(
        comodel_name='affiliation.insurance',
        string=_('Health Insurance'),
        ondelete='restrict',
        )
    
    department_id = fields.Many2one(
        comodel_name='affiliation.department',
        string='Department',
        ondelete='restrict',
    )
