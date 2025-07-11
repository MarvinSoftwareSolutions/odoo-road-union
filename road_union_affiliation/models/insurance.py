from odoo import models, fields

class Insurance(models.Model):
    _name = 'affiliation.insurance'
    _description = 'Health Insurance'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)