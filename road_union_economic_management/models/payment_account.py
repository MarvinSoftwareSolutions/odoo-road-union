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

    affiliate_type = fields.Char(
        string='Tipo de Afiliado',
        related='affiliate_id.affiliate_type_id.name',
        readonly=True,
        store=True  # Opcional: para mejor rendimiento en búsquedas
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
        readonly=True,
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
    odontology_installment = fields.Char(string="N° Cuota Odontología")
    
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
    
    def _update_subsequent_months_initial_balance(self):
        """
        Actualiza el saldo inicial y todos los campos dependientes 
        de todos los meses posteriores para este afiliado.
        """
        if not self.affiliate_id or not self.date_month or not self.date_year:
            return
            
        # Buscar todos los registros posteriores del mismo afiliado
        current_month = int(self.date_month)
        current_year = int(self.date_year)
        
        # Crear una fecha de comparación
        current_date = datetime(current_year, current_month, 1)
        
        # Buscar TODOS los registros del afiliado
        all_records = self.search([
            ('affiliate_id', '=', self.affiliate_id.id),
        ], order='date_year asc, date_month asc')
        
        # Filtrar solo los posteriores al actual
        subsequent_records = all_records.filtered(
            lambda r: datetime(int(r.date_year), int(r.date_month), 1) > current_date
        )
        
        if not subsequent_records:
            return
            
        # Procesar en orden cronológico (ya están ordenados por la query)
        for record in subsequent_records:
            # Recalcular el initial_balance (esto triggereará la cascada de cálculos)
            record._compute_initial_balance()
            
            # Forzar recálculo de campos dependientes
            record._compute_total_services()
            record._compute_total()
            record._compute_final_balance()

    @api.depends('affiliate_id', 'date_month', 'date_year')
    def _compute_initial_balance(self):
        """
        Calcula el saldo inicial como el saldo final del mes anterior.
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
            
            # Formatear mes anterior
            previous_month_str = str(previous_month).zfill(2)
            previous_year_str = str(previous_year)
            
            # Buscar el registro del mes anterior
            previous_record = self.search([
                ('affiliate_id', '=', record.affiliate_id.id),
                ('date_month', '=', previous_month_str),
                ('date_year', '=', previous_year_str)
            ], limit=1)
            
            if previous_record:
                # Asegurar que el registro anterior tenga su final_balance actualizado
                previous_record._compute_final_balance()
                record.initial_balance = previous_record.final_balance
            else:
                record.initial_balance = 0.0

    def write(self, vals):
        """
        Override write mejorado para propagar cambios correctamente.
        """
        # Campos que afectan el balance final
        balance_affecting_fields = [
            'pharmacy_total', 'optical_total', 'punilla_total', 'solar_caruso', 
            'parque_del_sol', 'salguero', 'tres_provincias', 'ecco_loan', 
            'emi_loan', 'emergency_loan', 'suoem_loan', 'tourism_total', 
            'aid_total', 'party_total', 'hall_total', 'odontology_total', 
            'union_fee', 'payments', 'pension_fund', 'meta4'
        ]
        
        result = super().write(vals)
        
        # Si se modificó algo que afecte el saldo final
        if any(field in vals for field in balance_affecting_fields):
            for record in self:
                # Recalcular campos del registro actual
                record._compute_total_services()
                record._compute_total()
                record._compute_final_balance()
                
                # Propagar a meses posteriores
                record._update_subsequent_months_initial_balance()
        
        return result

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