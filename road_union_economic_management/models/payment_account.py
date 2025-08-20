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
        string='Month'
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
            # 'domain': [
            #     ('date_month', '>=', date_from.strftime('%Y-%m-%d')),
            #     ('date_month', '<=', date_to.strftime('%Y-%m-%d'))
            # ],
            'context': {
                'group_by': ['date_year', 'date_month'],
                'default_date_year': str(today.year),
                'default_date_month': date_from.strftime('%m'),# Opcional: para crear nuevos registros en este mes
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