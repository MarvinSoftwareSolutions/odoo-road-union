from odoo import models, fields, api, _
from datetime import date


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

    age = fields.Integer(string="Edad", compute='_compute_age', store=False)

    birthday_str = fields.Char(string="Birthday", compute='_compute_birthday_str')

    def action_view_children(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Children of %s') % (self.name,),
            'res_model': 'affiliation.affiliate_child',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('road_union_affiliation.view_affiliate_child_tree_readonly').id, 'tree'),
                (self.env.ref('road_union_affiliation.view_affiliate_child_form_readonly').id, 'form')
            ],
            'domain': [('id', 'in', self.affiliate_child_ids.ids)],
            'context': {
                'default_affiliate_ids': [(6, 0, [self.id])],
                'from_button': True,
                },
            'target': 'current',
        }


    @api.depends('birth_date')
    def _compute_birthday_str(self):
        for record in self:
            if record.birth_date:
                record.birthday_str = record.birth_date.strftime('%d/%m')
            else:
                record.birthday_str = ''


    @api.depends('birth_date')
    def _compute_age(self):
        today = date.today()
        for record in self:
            if record.birth_date:
                born = record.birth_date
                age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
                record.age = age
            else:
                record.age = 0