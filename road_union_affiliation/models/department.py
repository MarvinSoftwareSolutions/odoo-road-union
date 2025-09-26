from odoo import models, fields

class Department(models.Model):
    _name = 'affiliation.department'
    _description = 'Departamento de trabajo del afiliado'

    name = fields.Char(string="Department Name", required=True)
    code = fields.Char(string="Code")
    active = fields.Boolean(default=True)
    delegate_name = fields.Char(string="Delegate Name")