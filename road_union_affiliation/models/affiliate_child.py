from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta

class AffiliateChild(models.Model):
    _inherit = 'affiliation.affiliate_child'
    
    # Campo computado para la edad
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
        help="Age calculated from birth date"
    )
    
    
    @api.depends('birth_date')
    def _compute_age(self):
        """Calcula la edad en años basada en la fecha de nacimiento"""
        for record in self:
            if record.birth_date:
                today = date.today()
                age = relativedelta(today, record.birth_date)
                record.age = age.years
            else:
                record.age = 0