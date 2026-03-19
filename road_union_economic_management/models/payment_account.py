from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

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
        store=True
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

    affiliate_number = fields.Integer(
        string="N° Afiliado",
        compute="_compute_affiliate_uid",
        inverse="_inverse_affiliate_uid",
        store=True,
    )

    @api.depends('affiliate_id')
    def _compute_affiliate_uid(self):
        for record in self:
            record.affiliate_number = record.affiliate_id.uid if record.affiliate_id else 0

    def _inverse_affiliate_uid(self):
        for record in self:
            if record.affiliate_number:
                affiliate = self.env['affiliation.affiliate'].search([
                    ('uid', '=', record.affiliate_number)
                ], limit=1)
                if affiliate:
                    record.affiliate_id = affiliate

    cuil = fields.Char(
        string="CUIL",
        related="affiliate_id.vat",
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

    _sql_constraints = [
        ('unique_affiliate_month_year',
         'unique(affiliate_id, date_month, date_year)',
         'Ya existe un resumen para este afiliado para este mes y año. '
         'Asegúrese de que cada afiliado tenga solo un resumen por mes/año.')
    ]

    id_benefit = fields.Char(
        string="ID/BENEFIT",
        related="affiliate_id.id_benefit",
    )
    
    # Campo helper para controlar readonly de initial_balance
    has_previous_month = fields.Boolean(
        string="Tiene mes anterior",
        compute='_compute_has_previous_month',
        store=True
    )

    @api.depends('affiliate_id', 'date_month', 'date_year')
    def _compute_has_previous_month(self):
        """Verifica si existe un registro del mes anterior"""
        for record in self:
            if not record.affiliate_id or not record.date_month or not record.date_year:
                record.has_previous_month = False
                continue
                
            current_month = int(record.date_month)
            current_year = int(record.date_year)
            
            if current_month == 1:
                previous_month = 12
                previous_year = current_year - 1
            else:
                previous_month = current_month - 1
                previous_year = current_year
            
            previous_month_str = str(previous_month).zfill(2)
            previous_year_str = str(previous_year)
            
            previous_record = self.search([
                ('affiliate_id', '=', record.affiliate_id.id),
                ('date_month', '=', previous_month_str),
                ('date_year', '=', previous_year_str)
            ], limit=1)
            
            record.has_previous_month = bool(previous_record)

    # Campo initial_balance con compute + inverse para permitir edición condicional
    initial_balance = fields.Float(
        string="Initial Balance", 
        compute='_compute_initial_balance',
        inverse='_inverse_initial_balance',
        store=True,
        group_operator='sum',
        help="Saldo inicial del mes. Se calcula automáticamente del mes anterior si existe, "
             "o puede ingresarse manualmente si es el primer mes del afiliado."
    )

    @api.depends('affiliate_id', 'date_month', 'date_year')
    def _compute_initial_balance(self):
        """
        Calcula el saldo inicial como el saldo final del mes anterior.
        Si no hay mes anterior, mantiene el valor existente o 0.
        """
        for record in self:
            if not record.affiliate_id or not record.date_month or not record.date_year:
                if not record.initial_balance:
                    record.initial_balance = 0.0
                continue
                
            current_month = int(record.date_month)
            current_year = int(record.date_year)
            
            if current_month == 1:
                previous_month = 12
                previous_year = current_year - 1
            else:
                previous_month = current_month - 1
                previous_year = current_year
            
            previous_month_str = str(previous_month).zfill(2)
            previous_year_str = str(previous_year)
            
            previous_record = self.search([
                ('affiliate_id', '=', record.affiliate_id.id),
                ('date_month', '=', previous_month_str),
                ('date_year', '=', previous_year_str)
            ], limit=1)
            
            if previous_record:
                # Si hay mes previo, SIEMPRE sobrescribir
                previous_record._compute_final_balance()
                record.initial_balance = previous_record.final_balance
            elif not record.initial_balance:
                # Si no hay mes previo y no tiene valor, poner 0
                record.initial_balance = 0.0

    def _inverse_initial_balance(self):
        """
        Método inverse para permitir escritura manual cuando NO hay mes previo.
        """
        for record in self:
            if record.has_previous_month:
                _logger.warning(
                    f"Intento de edición manual de initial_balance en registro con mes previo "
                    f"(Afiliado: {record.affiliate_id.name}, {record.date_month}/{record.date_year}). "
                    f"El valor será recalculado automáticamente."
                )
                # Recalcular inmediatamente desde mes anterior
                record._compute_initial_balance()

    # Service Totals
    pharmacy_installment = fields.Char(string="N° Cuota Farmacias")
    pharmacy_total = fields.Float(string="Todas las farmacias", group_operator='sum')

    optical_installment = fields.Char(string="N° Cuota Óptica")
    optical_total = fields.Float(string="Optica", group_operator='sum')

    punilla_installment = fields.Char(string="N° Cuota Punilla")
    punilla_total = fields.Float(string="Punilla", group_operator='sum')

    solar_installment = fields.Char(string="N° Cuota Solar")
    solar = fields.Float(string="Solar", group_operator='sum')
    caruso_installment = fields.Char(string="N° Cuota Caruso")
    caruso = fields.Float(string="Caruso", group_operator='sum')

    parque_del_sol_installment = fields.Char(string="N° Cuota Parque del Sol")
    parque_del_sol = fields.Float(string="Parque del Sol", group_operator='sum')
    salguero_installment = fields.Char(string="N° Cuota Salguero")
    salguero = fields.Float(string="Salguero", group_operator='sum')
    tres_provincias_installment = fields.Char(string="N° Cuota Tres Provincias")
    tres_provincias = fields.Float(string="Tres Provincias", group_operator='sum')

    ecco_installment = fields.Char(string="N° Cuota ECCO")
    ecco_loan = fields.Float(string="ECCO", group_operator='sum')
    emi_installment = fields.Char(string="N° Cuota EMI")
    emi_loan = fields.Float(string="EMI", group_operator='sum')
    emergency_installment = fields.Char(string="N° Cuota Urgencias")
    emergency_loan = fields.Float(string="URGENCIAS", group_operator='sum')
    suoem_installment = fields.Char(string="N° Cuota SUOEM")
    suoem_loan = fields.Float(string="SUOEM", group_operator='sum')

    tourism_installment = fields.Char(string="N° Cuota Turismo")
    tourism_total = fields.Float(string="Turismo", group_operator='sum')

    aid_installment = fields.Char(string="N° Cuota Ayudas")
    aid_total = fields.Float(string="AYUDA SOLIDARIA", group_operator='sum')

    party_installment = fields.Char(string="N° Cuota Fiesta")
    party_total = fields.Float(string="FIESTA", group_operator='sum')

    hall_installment = fields.Char(string="N° Cuota Salón")
    hall_total = fields.Float(string="Salon", group_operator='sum')

    odontology_installment = fields.Char(string="N° Cuota Odontología")
    odontology_total = fields.Float(string="Odontología", group_operator='sum')

    otros_1_installment = fields.Char(string="N° Cuota Otros 1")
    otros_1 = fields.Float(string="OTROS 1", group_operator='sum')
    otros_2_installment = fields.Char(string="N° Cuota Otros 2")
    otros_2 = fields.Float(string="OTROS 2", group_operator='sum')

    union_fee = fields.Float(
        string="CUOTA SINDICAL",
        compute='_compute_union_fee',
        store=True,
        group_operator='sum',
        help="Calculado automáticamente según clase y tipo de afiliado"
    )

    @api.depends('affiliate_id.category', 'affiliate_id.affiliate_type_id.name')
    def _compute_union_fee(self):
        """
        Calcula la cuota sindical según las reglas:
        - Activos: 1.5% del básico de su clase + 1.5% del básico de clase 15
        - Jubilados: 75% de lo que pagaría un activo (0.75 * cuota activo)
        Usa el historial mensual de básicos para obtener el valor correcto del mes.
        """
        History = self.env['affiliate.class.basic.history']
        for record in self:
            if not record.affiliate_id or not record.affiliate_id.category:
                record.union_fee = 0.0
                continue

            affiliate_class = record.affiliate_id.category
            affiliate_type = record.affiliate_id.affiliate_type_id.name if record.affiliate_id.affiliate_type_id else ''

            own_basic = History.get_basic_for_month(
                affiliate_class, record.date_month, record.date_year)
            class_15_basic = History.get_basic_for_month(
                15, record.date_month, record.date_year)

            is_retired = any(keyword in affiliate_type.lower()
                            for keyword in ['jubilado', 'pensionado', 'retirado'])

            record.union_fee = own_basic * 0.015 + class_15_basic * 0.015
            if is_retired:
                record.union_fee *= 0.75

    total_services = fields.Float(
        string="TOTAL SERVICIOS",
        compute='_compute_total_services',
        store=True,
        group_operator='sum'
    )

    total = fields.Float(
        string="TOTAL",
        compute='_compute_total',
        store=True,
        group_operator='sum'
    )

    payments = fields.Float(string="Pagos", group_operator='sum')
    pension_fund = fields.Float(string="CAJA DE JUBILACIONES", group_operator='sum')
    meta4 = fields.Float(string="META 4", group_operator='sum')

    final_balance = fields.Float(
        string="SALDO",
        compute='_compute_final_balance',
        store=True,
        group_operator='sum'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], default='draft', string="Status")

    @api.depends('affiliate_id.name')
    def _compute_affiliate_name(self):
        for record in self:
            record.affiliate_name = record.affiliate_id.name if record.affiliate_id else ''

    @api.depends('initial_balance', 'pharmacy_total', 'optical_total', 'punilla_total', 'solar', 'caruso', 
                 'parque_del_sol', 'salguero', 'tres_provincias', 'ecco_loan', 'emi_loan', 
                 'emergency_loan', 'suoem_loan', 'tourism_total', 'aid_total', 
                 'party_total', 'hall_total', 'odontology_total', 'otros_1', 'otros_2')
    def _compute_total_services(self):
        """Calcula el total de servicios incluyendo el saldo inicial."""
        for record in self:
            record.total_services = (
                record.initial_balance +
                record.pharmacy_total + record.optical_total + record.punilla_total +
                record.solar + record.caruso + record.parque_del_sol + 
                record.salguero + record.tres_provincias +
                record.ecco_loan + record.emi_loan + 
                record.emergency_loan + record.suoem_loan +
                record.tourism_total + record.aid_total + 
                record.party_total + record.hall_total + 
                record.odontology_total + record.otros_1 + record.otros_2
            )

    @api.depends('total_services', 'union_fee')
    def _compute_total(self):
        """Calcula el total: total servicios + cuota sindical"""
        for record in self:
            record.total = record.total_services + record.union_fee

    @api.depends('total', 'payments', 'pension_fund', 'meta4')
    def _compute_final_balance(self):
        """Calcula el saldo final: total - pagos - caja jub - meta 4"""
        for record in self:
            record.final_balance = (
                record.total - 
                record.payments - 
                record.pension_fund - 
                record.meta4
            )

    @api.model
    def get_current_month_stats(self):
        """Obtiene estadísticas del mes actual."""
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
        """Override create para recalcular saldos posteriores y aplicar planes de cuotas"""
        # Resolver affiliate_id desde affiliate_number si no viene affiliate_id
        if 'affiliate_number' in vals and not vals.get('affiliate_id'):
            affiliate = self.env['affiliation.affiliate'].search([
                ('uid', '=', vals['affiliate_number'])
            ], limit=1)
            if affiliate:
                vals['affiliate_id'] = affiliate.id
        record = super(AffiliatePaymentAccount, self).create(vals)
        # Asegurar que existan registros de historial para este mes
        if record.date_month and record.date_year:
            self.env['affiliate.class.basic.history'].ensure_month_exists(
                record.date_month, record.date_year)
        record._update_subsequent_months_initial_balance()
        # Aplicar planes de cuotas activos del afiliado
        active_plans = self.env['affiliate.installment.plan'].search([
            ('affiliate_id', '=', record.affiliate_id.id),
            ('state', '=', 'active'),
        ])
        for plan in active_plans:
            plan.apply_to_record(record)
        return record
    
    def _update_subsequent_months_initial_balance(self):
        """
        Actualiza el saldo inicial de todos los meses posteriores para este afiliado.
        """
        if not self.affiliate_id or not self.date_month or not self.date_year:
            return
            
        current_month = int(self.date_month)
        current_year = int(self.date_year)
        current_date = datetime(current_year, current_month, 1)
        
        all_records = self.search([
            ('affiliate_id', '=', self.affiliate_id.id),
        ], order='date_year asc, date_month asc')
        
        subsequent_records = all_records.filtered(
            lambda r: datetime(int(r.date_year), int(r.date_month), 1) > current_date
        )
        
        if not subsequent_records:
            return
            
        for record in subsequent_records:
            record._compute_initial_balance()
            record._compute_total_services()
            record._compute_total()
            record._compute_final_balance()

    def write(self, vals):
        """Override write para propagar cambios correctamente."""
        balance_affecting_fields = [
            'pharmacy_total', 'optical_total', 'punilla_total', 'solar', 'caruso',
            'parque_del_sol', 'salguero', 'tres_provincias', 'ecco_loan', 
            'emi_loan', 'emergency_loan', 'suoem_loan', 'tourism_total', 
            'aid_total', 'party_total', 'hall_total', 'odontology_total', 
            'otros_1', 'otros_2', 'union_fee', 'payments', 'pension_fund', 'meta4'
        ]
        
        result = super(AffiliatePaymentAccount, self).write(vals)
        
        if any(field in vals for field in balance_affecting_fields):
            for record in self:
                record._compute_total_services()
                record._compute_total()
                record._compute_final_balance()
                record._update_subsequent_months_initial_balance()
        
        # Si se modificó initial_balance manualmente (sin mes previo)
        if 'initial_balance' in vals:
            for record in self:
                if not record.has_previous_month:
                    record._update_subsequent_months_initial_balance()
        
        return result

    @api.model
    def create_monthly_records_for_all_affiliates(self, month=None, year=None):
        """
        Crea registros mensuales para TODOS los afiliados activos.
        """
        if not month or not year:
            today = datetime.now()
            month = today.strftime('%m')
            year = str(today.year)
        
        affiliates = self.env['affiliation.affiliate'].search([
            ('active', '=', True)
        ])
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for affiliate in affiliates:
            try:
                existing = self.search([
                    ('affiliate_id', '=', affiliate.id),
                    ('date_month', '=', month),
                    ('date_year', '=', year)
                ], limit=1)
                
                if existing:
                    skipped_count += 1
                    continue
                
                new_record = self.create({
                    'affiliate_id': affiliate.id,
                    'date_month': month,
                    'date_year': year,
                    'state': 'draft',
                })
                created_count += 1

                # Aplicar planes de cuotas activos
                active_plans = self.env['affiliate.installment.plan'].search([
                    ('affiliate_id', '=', affiliate.id),
                    ('state', '=', 'active'),
                ])
                for plan in active_plans:
                    plan.apply_to_record(new_record)

            except Exception as e:
                errors.append(f"Error con afiliado {affiliate.name}: {str(e)}")
                _logger.error(f"Error creating payment account for {affiliate.name}: {e}")
        
        # Asegurar que existan registros de historial de básicos para este mes
        self.env['affiliate.class.basic.history'].ensure_month_exists(month, year)

        result = {
            'created': created_count,
            'skipped': skipped_count,
            'total_affiliates': len(affiliates),
            'errors': errors,
            'month': month,
            'year': year,
        }

        _logger.info(f"Monthly records creation: {result}")
        return result

    @api.model
    def create_record_for_new_affiliate(self, affiliate_id):
        """Crea un registro para un nuevo afiliado en el mes actual."""
        today = datetime.now()
        month = today.strftime('%m')
        year = str(today.year)
        
        existing = self.search([
            ('affiliate_id', '=', affiliate_id),
            ('date_month', '=', month),
            ('date_year', '=', year)
        ], limit=1)
        
        if existing:
            return existing
        
        return self.create({
            'affiliate_id': affiliate_id,
            'date_month': month,
            'date_year': year,
            'state': 'draft',
        })

    @api.model
    def cron_create_monthly_records(self):
        """Tarea programada para crear registros mensuales automáticamente."""
        _logger.info("Iniciando creación automática de registros mensuales...")
        result = self.create_monthly_records_for_all_affiliates()
        
        if result['created'] > 0:
            message = f"""
            Se crearon automáticamente {result['created']} registros mensuales.
            Mes: {result['month']}/{result['year']}
            Afiliados procesados: {result['total_affiliates']}
            Ya existentes (omitidos): {result['skipped']}
            """
            _logger.info(message)
        
        return result

    def name_get(self):
        """Personaliza cómo se muestra el registro en relaciones Many2one."""
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


class AffiliateClassBasic(models.Model):
    _name = "affiliate.class.basic"
    _description = "Basic Amount by Affiliate Class"
    _order = "class_number"
    
    class_number = fields.Integer(
        string="Clase",
        required=True,
        help="Número de clase del afiliado"
    )
    
    class_index = fields.Float(
        string="Índice",
        required=True,
        help="Índice de básico en función de clase 1"
    )
    
    basic_amount = fields.Float(
        string="Básico",
        required=True,
        digits='Product Price',
        compute='_compute_basic_amount',
        store=True,
        readonly=False,
        help="Monto básico para esta clase"
    )
    
    # Campo auxiliar solo para la clase 1
    basic_amount_class1 = fields.Float(
        string="Básico Clase 1",
        digits='Product Price',
        help="Monto básico de referencia (solo para clase 1)"
    )
    
    active = fields.Boolean(
        string="Activo",
        default=True
    )
    
    _sql_constraints = [
        ('unique_class', 'unique(class_number)', 
         'Ya existe un básico definido para esta clase.')
    ]
    
    @api.depends('class_index', 'basic_amount_class1')
    def _compute_basic_amount(self):
        """
        Calcula el basic_amount multiplicando el basic_amount de clase 1
        por el class_index correspondiente.
        """
        for record in self:
            if record.class_number == 1:
                # Para clase 1, basic_amount es igual a basic_amount_class1
                record.basic_amount = record.basic_amount_class1
            else:
                # Para otras clases, buscar el basic_amount de clase 1
                class1_record = self.search([('class_number', '=', 1)], limit=1)
                if class1_record:
                    record.basic_amount = class1_record.basic_amount * record.class_index
                else:
                    record.basic_amount = 0.0
    
    def name_get(self):
        result = []
        for record in self:
            name = f"Clase {record.class_number} - ${record.basic_amount:,.2f}"
            result.append((record.id, name))
        return result
    
    def write(self, vals):
        """
        Override write para:
        1. Actualizar basic_amount_class1 si se modifica basic_amount en clase 1
        2. Recalcular union_fee cuando se modifica el básico (via historial)
        3. Propagar cambios a todas las clases cuando se modifica clase 1
        """
        result = super(AffiliateClassBasic, self).write(vals)

        # Si se modificó basic_amount en la clase 1, actualizar todas las demás clases
        if 'basic_amount' in vals:
            for record in self:
                if record.class_number == 1:
                    # Actualizar el campo auxiliar
                    if 'basic_amount_class1' not in vals:
                        super(AffiliateClassBasic, record).write({
                            'basic_amount_class1': vals['basic_amount']
                        })

                    # Recalcular todas las demás clases
                    other_classes = self.search([('class_number', '!=', 1)])
                    other_classes._compute_basic_amount()

                    # Crear historial del mes actual y recalcular cuotas
                    if not self.env.context.get('_skip_history_creation'):
                        today = datetime.now()
                        History = self.env['affiliate.class.basic.history']
                        History.set_class1_basic_for_month(
                            today.strftime('%m'), str(today.year), vals['basic_amount'])

        # Si se modificó basic_amount_class1, recalcular todas las clases
        if 'basic_amount_class1' in vals:
            all_classes = self.search([])
            all_classes._compute_basic_amount()
            if not self.env.context.get('_skip_history_creation'):
                today = datetime.now()
                class1 = self.search([('class_number', '=', 1)], limit=1)
                if class1:
                    History = self.env['affiliate.class.basic.history']
                    History.set_class1_basic_for_month(
                        today.strftime('%m'), str(today.year), class1.basic_amount)

        return result
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create para sincronizar basic_amount_class1 al crear clase 1
        """
        records = super(AffiliateClassBasic, self).create(vals_list)
        
        for record in records:
            if record.class_number == 1 and 'basic_amount' in vals_list[0]:
                super(AffiliateClassBasic, record).write({
                    'basic_amount_class1': record.basic_amount
                })
        
        return records
    
    def action_recalculate_all(self):
        """
        Acción de botón para recalcular todas las clases manualmente.
        """
        self.ensure_one()
        if self.class_number == 1:
            # Recalcular todas las clases
            all_classes = self.search([])
            all_classes._compute_basic_amount()
            # Crear historial del mes actual y recalcular cuotas
            today = datetime.now()
            History = self.env['affiliate.class.basic.history']
            History.set_class1_basic_for_month(
                today.strftime('%m'), str(today.year), self.basic_amount)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Recálculo completado',
                    'message': 'Se han recalculado todas las clases y cuotas sindicales.',
                    'type': 'success',
                    'sticky': False,
                }
            }