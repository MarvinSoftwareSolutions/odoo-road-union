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
    affiliate_number = fields.Integer(
        string="N° Afiliado",
        related="affiliate_id.uid",
    )


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

    # Aquí es donde se usa la restricción SQL
    _sql_constraints = [
        ('unique_affiliate_month_year',
         'unique(affiliate_id, date_month, date_year)',
         'Ya existe un resumen para este afiliado para este mes y año. '
         'Asegúrese de que cada afiliado tenga solo un resumen por mes/año.')
    ]

    # CAMBIO: ID/BENEFIT ahora puede contener letras y símbolos
    id_benefit = fields.Char(
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

    # CAMBIO: Solar y Caruso como campos separados
    solar = fields.Float(string="Solar", group_operator=False)
    caruso = fields.Float(string="Caruso", group_operator=False)
    
    parque_del_sol = fields.Float(string="Parque del Sol", group_operator=False)
    salguero = fields.Float(string="Salguero", group_operator=False)
    tres_provincias = fields.Float(string="Tres Provincias", group_operator=False)

    # CAMBIO: Préstamos con strings renombrados
    ecco_loan = fields.Float(string="ECCO", group_operator=False)
    emi_loan = fields.Float(string="EMI", group_operator=False)
    emergency_loan = fields.Float(string="URGENCIAS", group_operator=False)
    suoem_loan = fields.Float(string="SUOEM", group_operator=False)

    # Tourism
    tourism_total = fields.Float(string="Turismo", group_operator=False)
    tourism_installment = fields.Char(string="N° Cuota Turismo")

    # Aid - CAMBIO: Renombrado a AYUDA SOLIDARIA
    aid_total = fields.Float(string="AYUDA SOLIDARIA", group_operator=False)
    aid_installment = fields.Char(string="N° Cuota Ayudas")

    # Party
    party_total = fields.Float(string="FIESTA", group_operator=False)
    party_installment = fields.Char(string="N° Cuota Fiesta")

    # Hall
    hall_total = fields.Float(string="Salon", group_operator=False)
    hall_installment = fields.Char(string="N° Cuota Salón")

    # Odontology (renombrado de OTROS para consistencia)
    odontology_total = fields.Float(string="Odontología", group_operator=False)

    # CAMBIO: Agregar campos OTROS 1 y OTROS 2 como gastos adicionales
    otros_1 = fields.Float(string="OTROS 1", group_operator=False)
    otros_2 = fields.Float(string="OTROS 2", group_operator=False)

    union_fee = fields.Float(
        string="CUOTA SINDICAL",
        compute='_compute_union_fee',
        store=True,
        group_operator=False,
        help="Calculado automáticamente según clase y tipo de afiliado"
    )

    @api.depends('affiliate_id.category', 'affiliate_id.affiliate_type_id.name')
    def _compute_union_fee(self):
        """
        Calcula la cuota sindical según las reglas:
        - Activos: 1.5% del básico de su clase + 1.5% del básico de clase 15
        - Jubilados: 7% del básico de su clase
        """
        for record in self:
                
            # Si no hay afiliado o clase, cuota = 0
            if not record.affiliate_id or not record.affiliate_id.category:
                record.union_fee = 0.0
                continue
                
            affiliate_class = record.affiliate_id.category
            affiliate_type = record.affiliate_id.affiliate_type_id.name if record.affiliate_id.affiliate_type_id else ''
            
            # Buscar el básico de la clase del afiliado
            class_basic = self.env['affiliate.class.basic'].search([
                ('class_number', '=', affiliate_class),
                ('active', '=', True)
            ], limit=1)
            
            if not class_basic:
                record.union_fee = 0.0
                continue
                
            # Determinar si es jubilado (ajustar según tus tipos exactos)
            is_retired = any(keyword in affiliate_type.lower() for keyword in ['jubilado', 'pensionado', 'retirado'])
            
            # Activos: 1.5% del básico de su clase + 1.5% del básico de clase 15
            own_class_fee = class_basic.basic_amount * 0.015
            
            # Buscar básico de clase 15
            class_15_basic = self.env['affiliate.class.basic'].search([
                ('class_number', '=', 15),
                ('active', '=', True)
            ], limit=1)
            
            if class_15_basic:
                class_15_fee = class_15_basic.basic_amount * 0.015
                record.union_fee = own_class_fee + class_15_fee
            else:
                # Si no existe clase 15, solo usar el de su clase
                record.union_fee = own_class_fee
                    
            
            if is_retired:
                # Jubilados: 7% del básico de su clase
                record.union_fee = record.union_fee * 0.75


    total = fields.Float(
        string="TOTAL", 
        compute='_compute_total',
        store=True,
        group_operator=False
    )
    payments = fields.Float(string="Pagos", group_operator=False)
    
    # CAMBIO: Fondo de Pensión renombrado
    pension_fund = fields.Float(string="CAJA DE JUBILACIONES", group_operator=False)
    
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
        # CAMBIO: Actualizar campos que afectan el balance final (solar y caruso separados, más otros_1 y otros_2)
        balance_affecting_fields = [
            'pharmacy_total', 'optical_total', 'punilla_total', 'solar', 'caruso',
            'parque_del_sol', 'salguero', 'tres_provincias', 'ecco_loan', 
            'emi_loan', 'emergency_loan', 'suoem_loan', 'tourism_total', 
            'aid_total', 'party_total', 'hall_total', 'odontology_total', 
            'otros_1', 'otros_2', 'union_fee', 'payments', 'pension_fund', 'meta4'
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
    

    @api.model
    def create_monthly_records_for_all_affiliates(self, month=None, year=None):
        """
        Crea registros mensuales para TODOS los afiliados activos.
        Si no se especifica mes/año, usa el mes actual.
        
        :param month: Mes en formato '01'-'12'
        :param year: Año en formato '2025'
        :return: Diccionario con estadísticas de creación
        """
        if not month or not year:
            today = datetime.now()
            month = today.strftime('%m')
            year = str(today.year)
        
        # Buscar todos los afiliados activos
        affiliates = self.env['affiliation.affiliate'].search([
            ('active', '=', True)
        ])
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for affiliate in affiliates:
            try:
                # Verificar si ya existe un registro para este mes
                existing = self.search([
                    ('affiliate_id', '=', affiliate.id),
                    ('date_month', '=', month),
                    ('date_year', '=', year)
                ], limit=1)
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Crear el registro
                self.create({
                    'affiliate_id': affiliate.id,
                    'date_month': month,
                    'date_year': year,
                    'state': 'draft',
                })
                created_count += 1
                
            except Exception as e:
                errors.append(f"Error con afiliado {affiliate.name}: {str(e)}")
                _logger.error(f"Error creating payment account for {affiliate.name}: {e}")
        
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
        """
        Crea un registro para un nuevo afiliado en el mes actual.
        
        :param affiliate_id: ID del afiliado
        :return: Registro creado o False
        """
        today = datetime.now()
        month = today.strftime('%m')
        year = str(today.year)
        
        # Verificar si ya existe
        existing = self.search([
            ('affiliate_id', '=', affiliate_id),
            ('date_month', '=', month),
            ('date_year', '=', year)
        ], limit=1)
        
        if existing:
            return existing
        
        # Crear el registro
        return self.create({
            'affiliate_id': affiliate_id,
            'date_month': month,
            'date_year': year,
            'state': 'draft',
        })

    @api.model
    def cron_create_monthly_records(self):
        """
        Tarea programada que se ejecuta automáticamente cada mes.
        Crea registros para todos los afiliados del mes actual.
        """
        _logger.info("Iniciando creación automática de registros mensuales...")
        result = self.create_monthly_records_for_all_affiliates()
        
        # Opcional: Enviar notificación al administrador
        if result['created'] > 0:
            message = f"""
            Se crearon automáticamente {result['created']} registros mensuales.
            Mes: {result['month']}/{result['year']}
            Afiliados procesados: {result['total_affiliates']}
            Ya existentes (omitidos): {result['skipped']}
            """
            # Aquí puedes agregar lógica para enviar un email o notificación
            _logger.info(message)
        
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

    # CAMBIO: Actualizar el método _compute_total_services para incluir solar, caruso, otros_1 y otros_2
    @api.depends('initial_balance', 'pharmacy_total', 'optical_total', 'punilla_total', 'solar', 'caruso', 'parque_del_sol', 
                 'salguero', 'tres_provincias', 'ecco_loan', 'emi_loan', 
                 'emergency_loan', 'suoem_loan', 'tourism_total', 'aid_total', 
                 'party_total', 'hall_total', 'odontology_total', 'otros_1', 'otros_2')
    def _compute_total_services(self):
        """
        Calcula el total de servicios incluyendo el saldo inicial.
        """
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

class AffiliateClassBasic(models.Model):
    _name = "affiliate.class.basic"
    _description = "Basic Amount by Affiliate Class"
    _order = "class_number"

    class_number = fields.Integer(
        string="Clase",
        required=True,
        help="Número de clase del afiliado"
    )
    
    basic_amount = fields.Float(
        string="Básico",
        required=True,
        digits='Product Price',
        help="Monto básico para esta clase"
    )
    
    active = fields.Boolean(
        string="Activo",
        default=True
    )
    
    _sql_constraints = [
        ('unique_class', 'unique(class_number)', 
         'Ya existe un básico definido para esta clase.')
    ]
    
    def name_get(self):
        result = []
        for record in self:
            name = f"Clase {record.class_number} - ${record.basic_amount:,.2f}"
            result.append((record.id, name))
        return result

    def write(self, vals):
        """
        Override write para recalcular union_fee solo en mes actual y posteriores
        cuando se modifica el básico.
        """
        result = super(AffiliateClassBasic, self).write(vals)
        
        # Solo recalcular si se modificó el basic_amount
        if 'basic_amount' in vals:
            self._update_union_fees_from_current_month()
        
        return result

    def _update_union_fees_from_current_month(self):
        """
        Recalcula union_fee para todos los payment_account del mes actual
        y meses futuros que usen esta clase o clase 15 (para activos).
        """
        for class_basic in self:
            # Obtener mes y año actual
            today = datetime.now()
            current_month = today.strftime('%m')
            current_year = str(today.year)
            
            # Buscar todos los payment_account afectados por este básico
            PaymentAccount = self.env['affiliate.payment_account']
            
            # Caso 1: Afiliados que tienen esta clase directamente
            affected_affiliates = self.env['affiliation.affiliate'].search([
                ('category', '=', class_basic.class_number)
            ])
            
            # Caso 2: Si es clase 15, afecta a TODOS los activos
            if class_basic.class_number == 15:
                all_affiliates = self.env['affiliation.affiliate'].search([])
                # Filtrar solo activos
                active_affiliates = all_affiliates.filtered(
                    lambda a: a.affiliate_type_id and 
                    not any(keyword in a.affiliate_type_id.name.lower() 
                           for keyword in ['jubilado', 'pensionado', 'retirado'])
                )
                affected_affiliates |= active_affiliates
            
            # Buscar todos los payment_accounts de estos afiliados desde mes actual en adelante
            all_records = PaymentAccount.search([
                ('affiliate_id', 'in', affected_affiliates.ids),
            ])
            
            # Filtrar solo registros del mes actual y futuros
            current_date = datetime(int(current_year), int(current_month), 1)
            
            records_to_update = all_records.filtered(
                lambda r: datetime(int(r.date_year), int(r.date_month), 1) >= current_date
            )
            
            # Forzar recálculo del union_fee
            for record in records_to_update:
                record._compute_union_fee()
                # También recalcular los totales dependientes
                record._compute_total()
                record._compute_final_balance()
                # Y propagar a meses posteriores si es necesario
                record._update_subsequent_months_initial_balance()