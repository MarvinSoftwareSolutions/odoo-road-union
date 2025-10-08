from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class Affiliate(models.Model):
    _inherit = 'affiliation.affiliate'

    payment_account_ids = fields.One2many(
        comodel_name="affiliate.payment_account",
        inverse_name="affiliate_id",
        string="Economic Movements"
    )

    id_benefit = fields.Char(
        string='ID/BENEFIT',
        required=True,
    )

    _sql_constraints = [
        ('unique_id_benefit',
         'unique(id_benefit)',
         _('The ID/BENEFIT must be unique for each affiliate.'))
    ]

    @api.model
    def create(self, vals):
        # 1. Llamar al método create original para crear el registro del afiliado
        new_affiliate = super(Affiliate, self).create(vals)
        
        # 2. Obtener el mes y año actual
        today = date.today()
        current_month = today.strftime('%m') # Ej: '10'
        current_year = today.year          # Ej: 2024

        # 3. Crear el registro de gastos para el mes actual
        self.env['affiliate.pharmacy.expenses'].create({
            'affiliate_id': new_affiliate.id,
            'month': current_month,
            'year': current_year,
            # Los campos de gasto se inicializarán automáticamente a 0.0 (Float)
        })
        
        # Crear el registro del mes actual
        try:
            self.env['affiliate.payment_account'].create_record_for_new_affiliate(
                new_affiliate.id
            )
            _logger.info(f"Payment account creado automáticamente para {new_affiliate.name}")
        except Exception as e:
            _logger.warning(f"No se pudo crear payment account para {new_affiliate.name}: {e}")
            # No bloqueamos la creación del afiliado si falla esto
        
        return new_affiliate

    def action_create_current_month_payment(self):
        """
        Acción manual para crear el registro del mes actual
        si no existe (botón en la vista del afiliado).
        """
        for affiliate in self:
            record = self.env['affiliate.payment_account'].create_record_for_new_affiliate(
                affiliate.id
            )
            if record:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Registro Creado'),
                        'message': f'Se creó el registro mensual para {affiliate.name}',
                        'type': 'success',
                        'sticky': False,
                    }
                }

