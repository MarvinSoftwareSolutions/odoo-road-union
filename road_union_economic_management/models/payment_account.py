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

    # Información básica del afiliado
    affiliate_class = fields.Integer(
        string="Clase",
        related="affiliate_id.category",
        )
    affiliate_number = fields.Char(
        string="N° Afiliado",
        related="affiliate_id.uid",
    )


    dni = fields.Char(
        string="D.N.I",
        related="affiliate_id.personal_id",
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
        ('unique_affiliate_month_year',
         'unique(affiliate_id, date_month, date_year)',
         'Ya existe un resumen para este afiliado para este mes y año. '
         'Asegúrese de que cada afiliado tenga solo un resumen por mes/año.')
    ]

    id_benefit = fields.Integer(
        string="ID/BENEFIT",
        related="affiliate_id.id_benefit",
    )
    # Economic Summary
    initial_balance = fields.Float(
        string="Initial Balance", 
        compute='_compute_initial_balance',
        store=True,
        group_operator=False
    )

    # Service Totals
    pharmacy_total = fields.Float(string="Todas las farmacias", group_operator=False)
    pharmacy_installment = fields.Char(string="N° Cuota Farmacias")

    optical_total = fields.Float(string="Optica", group_operator=False)
    optical_installment = fields.Char(string="N° Cuota Óptica")
    
    punilla_total = fields.Float(string="Punilla", group_operator=False)

    # Servicios específicos
    solar_caruso = fields.Float(string="Solar Caruso", group_operator=False)
    parque_del_sol = fields.Float(string="Parque del Sol", group_operator=False)
    salguero = fields.Float(string="Salguero", group_operator=False)
    tres_provincias = fields.Float(string="Tres Provincias", group_operator=False)

    # Loans
    ecco_loan = fields.Float(string="Ecco PASADO COMO PRESTAMO", group_operator=False)
    emi_loan = fields.Float(string="Emi PASADO COMO PRESTAMO", group_operator=False)
    emergency_loan = fields.Float(string="Urgencias PASADO COMO PRESTAMO", group_operator=False)
    suoem_loan = fields.Float(string="Suoem PASADO COMO PRESTAMO", group_operator=False)
    loans_installment = fields.Char(string="N° Cuota Préstamos")

    # Tourism
    tourism_total = fields.Float(string="Turismo", group_operator=False)
    tourism_installment = fields.Char(string="N° Cuota Turismo")

    # Aid
    aid_total = fields.Float(string="AYUDAS", group_operator=False)
    aid_installment = fields.Char(string="N° Cuota Ayudas")

    # Party
    party_total = fields.Float(string="FIESTA", group_operator=False)
    party_installment = fields.Char(string="N° Cuota Fiesta")

    # Hall
    hall_total = fields.Float(string="Salon", group_operator=False)
    hall_installment = fields.Char(string="N° Cuota Salón")

    # Odontology (renombrado de OTROS para consistencia)
    odontology_total = fields.Float(string="OTROS", group_operator=False)

    # Totales y resumen económico
    total_services = fields.Float(
        string="TOTAL SERVICIOS", 
        compute='_compute_total_services',
        store=True,
        group_operator=False
    )
    union_fee = fields.Float(string="CUOTA SINDICAL", group_operator=False)
    total = fields.Float(
        string="TOTAL", 
        compute='_compute_total',
        store=True,
        group_operator=False
    )
    payments = fields.Float(string="Pagos", group_operator=False)
    pension_fund = fields.Float(string="CAJA JUB", group_operator=False)
    meta4 = fields.Float(string="META 4", group_operator=False)
    final_balance = fields.Float(
        string="SALDO", 
        compute='_compute_final_balance',
        store=True,
        group_operator=False
    )

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

    @api.model
    def create(self, vals):
        """
        Override create para recalcular saldos de meses posteriores cuando se crea un registro.
        """
        record = super().create(vals)
        record._update_subsequent_months_initial_balance()
        return record

    def write(self, vals):
        """
        Override write para recalcular saldos cuando se modifica el saldo final.
        """
        result = super().write(vals)
        # Si se modificó algo que afecte el saldo final, actualizar meses posteriores
        if any(field in vals for field in ['final_balance', 'total', 'payments', 'pension_fund', 'meta4', 
                                          'pharmacy_total', 'optical_total', 'punilla_total', 'solar_caruso', 
                                          'parque_del_sol', 'salguero', 'tres_provincias', 'ecco_loan', 
                                          'emi_loan', 'emergency_loan', 'suoem_loan', 'tourism_total', 
                                          'aid_total', 'party_total', 'hall_total', 'odontology_total', 
                                          'union_fee']):
            for record in self:
                record._update_subsequent_months_initial_balance()
        return result

    def _update_subsequent_months_initial_balance(self):
        """
        Actualiza el saldo inicial de todos los meses posteriores para este afiliado.
        """
        if not self.affiliate_id or not self.date_month or not self.date_year:
            return
            
        # Buscar todos los registros posteriores del mismo afiliado
        current_month = int(self.date_month)
        current_year = int(self.date_year)
        
        # Buscar registros del mismo año con mes mayor
        subsequent_records = self.search([
            ('affiliate_id', '=', self.affiliate_id.id),
            ('date_year', '=', self.date_year),
            ('date_month', '>', self.date_month),
        ])
        
        # Buscar registros de años posteriores
        subsequent_records |= self.search([
            ('affiliate_id', '=', self.affiliate_id.id),
            ('date_year', '>', self.date_year),
        ])
        
        # Forzar el recálculo del saldo inicial
        if subsequent_records:
            subsequent_records._compute_initial_balance()

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

    @api.depends('affiliate_id', 'date_month', 'date_year')
    def _compute_initial_balance(self):
        """
        Calcula el saldo inicial como el saldo final del mes anterior.
        Si no existe mes anterior, el saldo inicial es 0.
        """
        for record in self:
            if not record.affiliate_id or not record.date_month or not record.date_year:
                record.initial_balance = 0.0
                continue
                
            # Calcular mes y año anterior
            current_month = int(record.date_month)
            current_year = int(record.date_year)
            
            if current_month == 1:
                previous_month = 12
                previous_year = current_year - 1
            else:
                previous_month = current_month - 1
                previous_year = current_year
            
            # Formatear mes anterior con ceros a la izquierda
            previous_month_str = str(previous_month).zfill(2)
            previous_year_str = str(previous_year)
            
            # Buscar el registro del mes anterior
            previous_record = self.search([
                ('affiliate_id', '=', record.affiliate_id.id),
                ('date_month', '=', previous_month_str),
                ('date_year', '=', previous_year_str)
            ], limit=1)
            
            if previous_record:
                record.initial_balance = previous_record.final_balance
            else:
                record.initial_balance = 0.0

    @api.depends('initial_balance', 'pharmacy_total', 'optical_total', 'punilla_total', 'solar_caruso', 'parque_del_sol', 
                 'salguero', 'tres_provincias', 'ecco_loan', 'emi_loan', 
                 'emergency_loan', 'suoem_loan', 'tourism_total', 'aid_total', 
                 'party_total', 'hall_total', 'odontology_total')
    def _compute_total_services(self):
        """
        Calcula el total de servicios incluyendo el saldo inicial.
        """
        for record in self:
            record.total_services = (
                record.initial_balance +
                record.pharmacy_total + record.optical_total + record.punilla_total +
                record.solar_caruso + record.parque_del_sol + 
                record.salguero + record.tres_provincias +
                record.ecco_loan + record.emi_loan + 
                record.emergency_loan + record.suoem_loan +
                record.tourism_total + record.aid_total + 
                record.party_total + record.hall_total + 
                record.odontology_total
            )

    @api.depends('total_services', 'union_fee')
    def _compute_total(self):
        """
        Calcula el total: total servicios + cuota sindical
        """
        for record in self:
            record.total = record.total_services + record.union_fee

    @api.depends('total', 'payments', 'pension_fund', 'meta4')
    def _compute_final_balance(self):
        """
        Calcula el saldo final: total - pagos - caja jub - meta 4
        """
        for record in self:
            record.final_balance = (
                record.total - 
                record.payments - 
                record.pension_fund - 
                record.meta4
            )

    # Hacer los campos computados
    total_services = fields.Float(
        string="TOTAL SERVICIOS", 
        compute='_compute_total_services',
        store=True,
        group_operator=False
    )