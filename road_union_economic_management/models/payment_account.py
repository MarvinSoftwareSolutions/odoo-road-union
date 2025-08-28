from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime

class AffiliatePaymentAccount(models.Model):
    _name = "affiliate.payment_account"
    _description = "Affiliate Monthly Economic Summary"
    _order = "date_month desc"

    affiliate_id = fields.Many2one(
        comodel_name="affiliation.affiliate",
        string="Affiliate",
        required=True,
        ondelete="cascade"
    )

    affiliate_name = fields.Char(
        string='Nombre del afiliado',
        compute='_compute_affiliate_name',
        store=True
    )

    date_month = fields.Selection(
        selection=[
            ('01', 'January'),
            ('02', 'February'),
            ('03', 'March'),
            ('04', 'April'),
            ('05', 'May'),
            ('06', 'June'),
            ('07', 'July'),
            ('08', 'August'),
            ('09', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Month',
        required=True,
    )

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in
                reversed(range(current_year - 100, current_year + 1))]

    date_year = fields.Selection(
        selection=_get_year_selection,
        string='Year',
        required=True
    )

    # Aquí es donde se usa la restricción SQL
    _sql_constraints = [
        ('unique_affiliate_month_year', # Nombre único de la restricción
         'unique(affiliate_id, date_month, date_year)', # Tipo de restricción: combinación única de estos 3 campos
         'Ya existe un resumen para este afiliado para este mes y año. ' # Mensaje de error
         'Asegúrese de que cada afiliado tenga solo un resumen por mes/año.')
    ]

    id_benefit = fields.Float(string="ID/BENEFIT", group_operator=False)

    # Service Totals
    pharmacy_total = fields.Float(string="Pharmacies", group_operator=False)
    optical_total = fields.Float(string="Optical", group_operator=False)
    tourism_total = fields.Float(string="Tourism", group_operator=False)
    aid_total = fields.Float(string="Aid", group_operator=False)
    party_total = fields.Float(string="Party", group_operator=False)
    hall_total = fields.Float(string="Hall", group_operator=False)
    odontology_total = fields.Float(string="Odontology", group_operator=False)

    # Loans
    ecco_loan = fields.Float(string="Ecco Loan", group_operator=False)
    emi_loan = fields.Float(string="Emi Loan", group_operator=False)
    emergency_loan = fields.Float(string="Emergency Loan", group_operator=False)
    suoem_loan = fields.Float(string="Suoem Loan", group_operator=False)

    # Economic Summary
    initial_balance = fields.Float(string="Initial Balance", group_operator=False)
    union_fee = fields.Float(string="Union Fee", group_operator=False)
    payments = fields.Float(string="Payments", group_operator=False)
    pension_fund = fields.Float(string="Pension Fund", group_operator=False)
    total = fields.Float(string="Total", group_operator=False)
    final_balance = fields.Float(string="Final Balance", group_operator=False)

    # Optional: summary status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', string="Status")

    @api.depends('affiliate_id.name')
    def _compute_affiliate_name(self):
        for record in self:
            record.affiliate_name = record.affiliate_id.name if record.affiliate_id else ''

    @api.model
    def action_open_current_month_summary(self):
        """
        Abre la vista de resúmenes económicos mensuales.
        """
        today = date.today()
        # Calcula el primer día del mes actual
        date_from = today.replace(day=1)
        # Calcula el último día del mes actual
        date_to = today + relativedelta(months=1, day=1, days=-1)

        return {
            'name': "Resúmenes",
            'res_model': 'affiliate.payment_account',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('road_union_economic_management.view_payment_account_tree_grouped').id, 'tree'),
                (self.env.ref('road_union_economic_management.view_payment_account_current_month_tree').id, 'tree'),
                (False, 'form'),
            ],
            'context': {
                'group_by': ['date_year', 'date_month'],
                'default_date_year': str(today.year),
                'default_date_month': date_from.strftime('%m'),
            },
            'help': """
                <p class="o_view_nocontent_smiling_face">
                    No hay resúmenes económicos para el mes actual.
                </p>
            """,
            'search_view_id': self.env.ref('road_union_economic_management.view_affiliate_payment_account_search').id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
# Agregar estos métodos a la clase AffiliatePaymentAccount

    @api.model
    def action_open_current_month_only(self):
        """
        Abre la vista específica para el mes y año actuales únicamente.
        """
        today = date.today()
        current_month = today.strftime('%m')
        current_year = str(today.year)
        
        return {
            'name': f"Resúmenes - {today.strftime('%B %Y')}",
            'res_model': 'affiliate.payment_account',
            'view_mode': 'tree',
            'view_id': self.env.ref('road_union_economic_management.view_payment_account_current_month_only_tree').id,
            'domain': [('date_month', '=', current_month), ('date_year', '=', current_year)],
            'context': {
                'default_date_month': current_month,
                'default_date_year': current_year,
                'search_default_filter_current_month': 1,
            },
            'help': f"""
                <p class="o_view_nocontent_smiling_face">
                    No hay resúmenes económicos para {today.strftime('%B %Y')}.
                </p>
                <p>
                    Haga clic en "Crear" para agregar un nuevo resumen económico mensual.
                </p>
            """,
            'search_view_id': self.env.ref('road_union_economic_management.view_payment_account_current_month_search').id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    @api.model
    def get_current_month_stats(self):
        """
        Obtiene estadísticas del mes actual.
        """
        today = date.today()
        current_month = today.strftime('%m')
        current_year = str(today.year)
        
        records = self.search([
            ('date_month', '=', current_month),
            ('date_year', '=', current_year)
        ])
        
        return {
            'total_affiliates': len(records),
            'total_confirmed': len(records.filtered(lambda r: r.state == 'confirmed')),
            'total_draft': len(records.filtered(lambda r: r.state == 'draft')),
            'total_final_balance': sum(records.mapped('final_balance')),
            'month_name': today.strftime('%B'),
            'year': current_year,
        }

    def name_get(self):
        """
        Personaliza cómo se muestra el registro en relaciones Many2one.
        """
        result = []
        for record in self:
            month_names = {
                '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
                '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
                '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
            }
            month_name = month_names.get(record.date_month, record.date_month)
            name = f"{record.affiliate_name} - {month_name} {record.date_year}"
            result.append((record.id, name))
        return result