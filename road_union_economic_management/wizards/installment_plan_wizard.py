from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ..models.installment_plan import PROVIDER_SELECTION


class InstallmentPlanWizard(models.TransientModel):
    _name = 'installment.plan.wizard'
    _description = 'Wizard para crear Plan de Cuotas'

    affiliate_id = fields.Many2one(
        'affiliation.affiliate',
        string='Afiliado',
        required=True,
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
    start_month = fields.Selection(
        selection=[
            ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'),
            ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
            ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Septiembre'),
            ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
        ],
        string='Mes de Inicio',
        required=True,
    )

    @api.model
    def _get_year_selection(self):
        from datetime import datetime
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in
                reversed(range(current_year - 10, current_year + 10))]

    start_year = fields.Selection(
        selection=_get_year_selection,
        string='Año de Inicio',
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            record = self.env['affiliate.payment_account'].browse(active_id)
            if record.exists():
                res['affiliate_id'] = record.affiliate_id.id
                res['start_month'] = record.date_month
                res['start_year'] = record.date_year
        return res

    def action_create_plan(self):
        self.ensure_one()
        plan = self.env['affiliate.installment.plan'].create({
            'affiliate_id': self.affiliate_id.id,
            'provider_field': self.provider_field,
            'total_amount': self.total_amount,
            'total_installments': self.total_installments,
            'start_month': self.start_month,
            'start_year': self.start_year,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Plan de cuotas creado'),
                'message': _('Se creó el plan de %s cuotas de $%.2f. Se aplicaron %d cuotas a registros existentes.') % (
                    plan.total_installments, plan.installment_amount, plan.installments_applied),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
