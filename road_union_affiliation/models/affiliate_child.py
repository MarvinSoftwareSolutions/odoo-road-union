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
    
    # Campo computado para mostrar UIDs de los padres
    affiliate_uids = fields.Char(
        string='N° Afiliado (Padres)',
        compute='_compute_affiliate_uids',
        store=True,
    )

    # Campo helper para importación por nombre
    affiliate_parent_name = fields.Char(
        string='Nombre del Padre/Madre (para importación)',
        help='Campo auxiliar para facilitar la importación. Ingrese el nombre exacto del afiliado.'
    )

    # Campo helper para importación por UID
    affiliate_parent_uid = fields.Integer(
        string='N° Afiliado del Padre/Madre (para importación)',
        help='Campo auxiliar para facilitar la importación. Ingrese el número de afiliado.'
    )
    
    @api.depends('affiliate_ids.uid')
    def _compute_affiliate_uids(self):
        for record in self:
            record.affiliate_uids = ', '.join(
                str(uid) for uid in record.affiliate_ids.mapped('uid') if uid
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
    
    @api.model
    def _get_affiliate_by_name(self, name):
        """Helper para importación: busca afiliado por nombre"""
        if not name:
            return False
        affiliate = self.env['affiliation.affiliate'].search([('name', '=', name)], limit=1)
        return affiliate.id if affiliate else False
    
    @api.model
    def create(self, vals):
        """Override para procesar affiliate_parent_name y affiliate_parent_uid en importación"""
        if 'affiliate_parent_uid' in vals and vals['affiliate_parent_uid']:
            parent_uid = vals.pop('affiliate_parent_uid')
            affiliate = self.env['affiliation.affiliate'].search([
                ('uid', '=', int(parent_uid))
            ], limit=1)
            if affiliate:
                if 'affiliate_ids' not in vals:
                    vals['affiliate_ids'] = []
                vals['affiliate_ids'] = [(4, affiliate.id)]
                self._update_parent_role(affiliate)

        if 'affiliate_parent_name' in vals and vals['affiliate_parent_name']:
            parent_name = vals.pop('affiliate_parent_name')
            affiliate = self.env['affiliation.affiliate'].search([
                ('name', '=', parent_name)
            ], limit=1)
            if affiliate:
                if 'affiliate_ids' not in vals:
                    vals['affiliate_ids'] = []
                vals['affiliate_ids'] = [(4, affiliate.id)]
                self._update_parent_role(affiliate)
        
        # Crear el registro del hijo
        child = super(AffiliateChild, self).create(vals)
        
        # Si se vinculó mediante affiliate_ids directamente, actualizar parent_role
        if 'affiliate_ids' in vals and vals['affiliate_ids']:
            for command in vals['affiliate_ids']:
                # command puede ser (4, id) o (6, 0, [ids])
                if command[0] == 4:  # (4, id) - link
                    affiliate = self.env['affiliation.affiliate'].browse(command[1])
                    self._update_parent_role(affiliate)
                elif command[0] == 6:  # (6, 0, [ids]) - replace
                    affiliates = self.env['affiliation.affiliate'].browse(command[2])
                    for affiliate in affiliates:
                        self._update_parent_role(affiliate)
        
        return child
    
    def _update_parent_role(self, affiliate):
        """Actualiza el parent_role del afiliado según su género"""
        if not affiliate:
            return
        
        # Solo actualizar si parent_role está vacío o es 'no'
        if not affiliate.parent_role or affiliate.parent_role == 'no':
            if affiliate.gender == 'female':
                affiliate.write({'parent_role': 'mother'})
            else:
                # Para male, other, not_report → por defecto 'father'
                affiliate.write({'parent_role': 'father'})
    
    def write(self, vals):
        """Override write para actualizar parent_role cuando se modifican affiliate_ids"""
        result = super(AffiliateChild, self).write(vals)
        
        if 'affiliate_ids' in vals:
            # Actualizar parent_role de los afiliados vinculados
            for child in self:
                for affiliate in child.affiliate_ids:
                    self._update_parent_role(affiliate)
        
        return result