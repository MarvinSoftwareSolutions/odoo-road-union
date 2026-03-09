from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

# Mapeo: campo monto en payment_account → campo cuota en payment_account
PROVIDER_INSTALLMENT_MAP = {
    'pharmacy_total': 'pharmacy_installment',
    'optical_total': 'optical_installment',
    'punilla_total': 'punilla_installment',
    'solar': 'solar_installment',
    'caruso': 'caruso_installment',
    'parque_del_sol': 'parque_del_sol_installment',
    'salguero': 'salguero_installment',
    'tres_provincias': 'tres_provincias_installment',
    'ecco_loan': 'ecco_installment',
    'emi_loan': 'emi_installment',
    'emergency_loan': 'emergency_installment',
    'suoem_loan': 'suoem_installment',
    'tourism_total': 'tourism_installment',
    'aid_total': 'aid_installment',
    'party_total': 'party_installment',
    'hall_total': 'hall_installment',
    'odontology_total': 'odontology_installment',
    'otros_1': 'otros_1_installment',
    'otros_2': 'otros_2_installment',
}

PROVIDER_SELECTION = [
    ('pharmacy_total', 'Farmacias'),
    ('optical_total', 'Óptica'),
    ('punilla_total', 'Punilla'),
    ('solar', 'Solar'),
    ('caruso', 'Caruso'),
    ('parque_del_sol', 'Parque del Sol'),
    ('salguero', 'Salguero'),
    ('tres_provincias', 'Tres Provincias'),
    ('ecco_loan', 'ECCO'),
    ('emi_loan', 'EMI'),
    ('emergency_loan', 'Urgencias'),
    ('suoem_loan', 'SUOEM'),
    ('tourism_total', 'Turismo'),
    ('aid_total', 'Ayuda Solidaria'),
    ('party_total', 'Fiesta'),
    ('hall_total', 'Salón'),
    ('odontology_total', 'Odontología'),
    ('otros_1', 'Otros 1'),
    ('otros_2', 'Otros 2'),
]

MONTH_SELECTION = [
    ('01', 'Enero'),
    ('02', 'Febrero'),
    ('03', 'Marzo'),
    ('04', 'Abril'),
    ('05', 'Mayo'),
    ('06', 'Junio'),
    ('07', 'Julio'),
    ('08', 'Agosto'),
    ('09', 'Septiembre'),
    ('10', 'Octubre'),
    ('11', 'Noviembre'),
    ('12', 'Diciembre'),
]


class AffiliateInstallmentPlan(models.Model):
    _name = 'affiliate.installment.plan'
    _description = 'Plan de Cuotas de Proveedor'
    _order = 'create_date desc'

    affiliate_id = fields.Many2one(
        'affiliation.affiliate',
        string='Afiliado',
        required=True,
        ondelete='cascade',
    )
    provider_field = fields.Selection(
        PROVIDER_SELECTION,
        string='Proveedor',
        required=True,
    )
    total_amount = fields.Float(
        string='Monto Total',
        required=True,
    )
    total_installments = fields.Integer(
        string='Cantidad de Cuotas',
        required=True,
    )
    installments_applied = fields.Integer(
        string='Cuotas Aplicadas',
        default=0,
        readonly=True,
    )
    installment_amount = fields.Float(
        string='Monto por Cuota',
        compute='_compute_installment_amount',
        store=True,
    )
    remaining_installments = fields.Integer(
        string='Cuotas Restantes',
        compute='_compute_remaining',
    )
    state = fields.Selection([
        ('active', 'Activo'),
        ('done', 'Completado'),
        ('cancelled', 'Cancelado'),
    ], default='active', string='Estado')

    start_month = fields.Selection(
        MONTH_SELECTION,
        string='Mes de Inicio',
        required=True,
        default=lambda self: datetime.now().strftime('%m'),
    )

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in
                reversed(range(current_year - 10, current_year + 10))]

    start_year = fields.Selection(
        selection=_get_year_selection,
        string='Año de Inicio',
        required=True,
        default=lambda self: str(datetime.now().year),
    )

    @api.constrains('affiliate_id', 'provider_field', 'state')
    def _check_unique_active_plan(self):
        for record in self:
            if record.state == 'active':
                existing = self.search([
                    ('affiliate_id', '=', record.affiliate_id.id),
                    ('provider_field', '=', record.provider_field),
                    ('state', '=', 'active'),
                    ('id', '!=', record.id),
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _('Ya existe un plan de cuotas activo para este afiliado y proveedor. '
                          'Cancele o complete el plan existente antes de crear uno nuevo.')
                    )

    @api.depends('total_amount', 'total_installments')
    def _compute_installment_amount(self):
        for record in self:
            if record.total_installments > 0:
                record.installment_amount = record.total_amount / record.total_installments
            else:
                record.installment_amount = 0.0

    @api.depends('total_installments', 'installments_applied')
    def _compute_remaining(self):
        for record in self:
            record.remaining_installments = record.total_installments - record.installments_applied

    @api.constrains('total_amount', 'total_installments')
    def _check_values(self):
        for record in self:
            if record.total_amount <= 0:
                raise ValidationError(_('El monto total debe ser mayor a 0.'))
            if record.total_installments <= 0:
                raise ValidationError(_('La cantidad de cuotas debe ser mayor a 0.'))

    def apply_to_record(self, payment_account_record):
        """
        Aplica la cuota correspondiente a un registro de payment_account.
        Escribe el monto en el campo del proveedor y la etiqueta de cuota.
        """
        self.ensure_one()
        if self.state != 'active':
            return

        # Verificar que el mes/año del registro es >= start_month/year del plan
        record_date = int(payment_account_record.date_year) * 100 + int(payment_account_record.date_month)
        plan_start_date = int(self.start_year) * 100 + int(self.start_month)
        if record_date < plan_start_date:
            return

        current_installment = self.installments_applied + 1
        installment_label = f"{current_installment}/{self.total_installments}"
        installment_field = PROVIDER_INSTALLMENT_MAP.get(self.provider_field)

        vals = {
            self.provider_field: self.installment_amount,
        }
        if installment_field:
            vals[installment_field] = installment_label

        payment_account_record.write(vals)

        self.write({
            'installments_applied': current_installment,
            'state': 'done' if current_installment >= self.total_installments else 'active',
        })

    @api.model
    def create(self, vals):
        record = super().create(vals)
        record._apply_to_existing_records()
        return record

    def _apply_to_existing_records(self):
        """Aplica cuotas a registros mensuales ya existentes desde el mes de inicio."""
        self.ensure_one()
        if self.state != 'active':
            return

        existing_records = self.env['affiliate.payment_account'].search([
            ('affiliate_id', '=', self.affiliate_id.id),
        ], order='date_year asc, date_month asc')

        plan_start = int(self.start_year) * 100 + int(self.start_month)

        for rec in existing_records:
            if self.state != 'active':
                break
            rec_date = int(rec.date_year) * 100 + int(rec.date_month)
            if rec_date >= plan_start:
                self.apply_to_record(rec)

    def action_apply_to_existing(self):
        """Botón para aplicar manualmente a registros existentes."""
        for record in self:
            record._apply_to_existing_records()

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_reactivate(self):
        for record in self:
            if record.installments_applied < record.total_installments:
                record.state = 'active'
