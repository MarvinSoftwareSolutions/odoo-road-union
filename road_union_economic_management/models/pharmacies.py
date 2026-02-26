# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Mapeo simple de meses
MONTH_MAP = {
    '01': 1, '02': 2, '03': 3, '04': 4, '05': 5, '06': 6,
    '07': 7, '08': 8, '09': 9, '10': 10, '11': 11, '12': 12,
}

# La clave es el mes actual, el valor es (mes_anterior, año_ajuste)
PREVIOUS_MONTH_MAP = {
    '01': ('12', -1),
    '02': ('01', 0),
    '03': ('02', 0),
    '04': ('03', 0),
    '05': ('04', 0),
    '06': ('05', 0),
    '07': ('06', 0),
    '08': ('07', 0),
    '09': ('08', 0),
    '10': ('09', 0),
    '11': ('10', 0),
    '12': ('11', 0),
}

# Mapa inverso: dado un mes, cuál es el siguiente
NEXT_MONTH_MAP = {
    '01': ('02', 0),
    '02': ('03', 0),
    '03': ('04', 0),
    '04': ('05', 0),
    '05': ('06', 0),
    '06': ('07', 0),
    '07': ('08', 0),
    '08': ('09', 0),
    '09': ('10', 0),
    '10': ('11', 0),
    '11': ('12', 0),
    '12': ('01', 1),
}


class AffiliatePharmacyExpenses(models.Model):
    _name = "affiliate.pharmacy.expenses"
    _description = "Gastos mensuales por farmacia"

    affiliate_id = fields.Many2one("affiliation.affiliate", string="Afiliado", required=True)
    month = fields.Selection([
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
    ], string="Mes", required=True)
    year = fields.Integer(string="Año", required=True)

    # ========== NUEVO: Líneas dinámicas de gastos ==========
    linea_gastos_ids = fields.One2many(
        'affiliate.pharmacy.expense.line',
        'expense_id',
        string='Gastos por Farmacia'
    )

    # ========== Campos computados desde las líneas ==========
    suma_mes = fields.Float(
        string="Suma Mes", 
        compute="_compute_totales_from_lines", 
        store=True
    )
    
    vta_libre = fields.Float(
        string="VTA LIBRE", 
        compute="_compute_totales_from_lines", 
        store=True
    )
    
    # ========== Campos calculados (igual que antes) ==========
    descuento_realizado = fields.Float(
        string="Descuento Realizado", 
        compute="_compute_descuento_realizado", 
        store=True
    )
    
    desc_afil = fields.Float(
        string="Desc. Afil.", 
        compute="_compute_desc_afil", 
        store=True
    )
    
    disponible_40 = fields.Float(
        string="Disponible al 40%", 
        compute="_compute_disponible_40", 
        store=True
    )

    saldo_acumulado = fields.Float(
        string="Saldo Acumulado", 
        compute="_compute_saldo_acumulado", 
        store=True,
        help="Suma del Saldo Acumulado del mes anterior + Suma Mes del mes actual para el mismo afiliado."
    )

    # ========== NUEVO: Cálculo de totales desde líneas ==========
    @api.depends('linea_gastos_ids.gasto_plan', 'linea_gastos_ids.gasto_venta_libre')
    def _compute_totales_from_lines(self):
        for rec in self:
            rec.suma_mes = sum(rec.linea_gastos_ids.mapped('gasto_plan'))
            rec.vta_libre = sum(rec.linea_gastos_ids.mapped('gasto_venta_libre'))

    @api.depends('suma_mes', 'saldo_acumulado')
    def _compute_descuento_realizado(self):
        """
        Fórmula Excel: =SI((Q+R)<125000;Q*0,4;SI(R>125000;0;(125000-R)*0,4))
        Donde Q = suma_mes, R = saldo_acumulado
        """
        for rec in self:
            q = rec.suma_mes
            r = rec.saldo_acumulado
            
            if (q + r) < 125000:
                rec.descuento_realizado = q * 0.4
            elif r > 125000:
                rec.descuento_realizado = 0
            else:
                rec.descuento_realizado = (125000 - r) * 0.4

    @api.depends('suma_mes', 'descuento_realizado', 'vta_libre')
    def _compute_desc_afil(self):
        """Desc. Afil. = Suma Mes - Descuento Realizado + VTA LIBRE"""
        for rec in self:
            rec.desc_afil = rec.suma_mes - rec.descuento_realizado + rec.vta_libre

    @api.depends('suma_mes', 'saldo_acumulado')
    def _compute_disponible_40(self):
        """Disponible al 40% = 125000 - (suma_mes + saldo_acumulado)"""
        for rec in self:
            rec.disponible_40 = 125000 - (rec.suma_mes + rec.saldo_acumulado)

    @api.depends('affiliate_id', 'year', 'month', 'suma_mes')
    def _compute_saldo_acumulado(self):
        for rec in self:
            saldo_mes_anterior = 0.0
            
            current_month = rec.month
            current_year = rec.year

            if current_month not in PREVIOUS_MONTH_MAP:
                rec.saldo_acumulado = rec.suma_mes
                continue

            prev_month, year_adjustment = PREVIOUS_MONTH_MAP[current_month]
            prev_year = current_year + year_adjustment

            previous_record = self.search([
                ('affiliate_id', '=', rec.affiliate_id.id),
                ('month', '=', prev_month),
                ('year', '=', prev_year),
            ], limit=1)

            if previous_record:
                saldo_mes_anterior = previous_record.saldo_acumulado

            rec.saldo_acumulado = saldo_mes_anterior + rec.suma_mes

    # ========== NUEVO: Generar líneas automáticamente ==========
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._generate_pharmacy_lines()
            record._recalculate_future_months()
        return records

    def write(self, vals):
        res = super().write(vals)
        # Solo recalculamos si cambiaron campos que afectan los totales
        if any(field in vals for field in ['month', 'year', 'affiliate_id', 'linea_gastos_ids']):
            for record in self:
                record._recalculate_future_months()
        return res

    def _generate_pharmacy_lines(self):
        """Genera automáticamente líneas para todas las farmacias activas"""
        self.ensure_one()
        
        # Obtener farmacias activas
        farmacias = self.env['sindicato.proveedor'].search([
            ('tipo', '=', 'farmacia'),
            ('activo', '=', True)
        ])
        
        # Farmacias que ya tienen línea
        farmacias_existentes = self.linea_gastos_ids.mapped('farmacia_id')
        
        # Crear líneas para farmacias faltantes
        for farmacia in farmacias:
            if farmacia not in farmacias_existentes:
                self.env['affiliate.pharmacy.expense.line'].create({
                    'expense_id': self.id,
                    'farmacia_id': farmacia.id,
                    'gasto_plan': 0.0,
                    'gasto_venta_libre': 0.0,
                })

    def action_refresh_pharmacy_lines(self):
        """Acción manual para actualizar las líneas de farmacias"""
        for record in self:
            record._generate_pharmacy_lines()
        return True

    def _recalculate_future_months(self):
        """Recalcula el saldo acumulado de todos los meses posteriores al actual"""
        self.ensure_one()
        
        if not self.month or not self.year:
            return

        current_month = self.month
        current_year = self.year
        
        # Buscamos todos los meses posteriores para el mismo afiliado
        while True:
            if current_month not in NEXT_MONTH_MAP:
                break
                
            next_month, year_adjustment = NEXT_MONTH_MAP[current_month]
            next_year = current_year + year_adjustment
            
            # Buscamos el registro del siguiente mes
            next_record = self.search([
                ('affiliate_id', '=', self.affiliate_id.id),
                ('month', '=', next_month),
                ('year', '=', next_year),
            ], limit=1)
            
            if not next_record:
                # No hay más meses registrados hacia adelante
                break
            
            # Forzamos el recálculo del saldo acumulado
            next_record._compute_saldo_acumulado()
            
            # Avanzamos al siguiente mes
            current_month = next_month
            current_year = next_year

    _sql_constraints = [
        ('unique_affiliate_month_year',
         'UNIQUE(affiliate_id, month, year)',
         'Ya existe un registro para este afiliado en este mes y año')
    ]

class AffiliatePharmacyExpenseLine(models.Model):
    _name = 'affiliate.pharmacy.expense.line'
    _description = 'Línea de Gasto por Farmacia'
    _rec_name = 'farmacia_id'

    expense_id = fields.Many2one(
        'affiliate.pharmacy.expenses',
        string='Gasto Mensual',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    affiliate_id = fields.Many2one(
        'affiliation.affiliate',
        related='expense_id.affiliate_id',
        string='Afiliado',
        store=True,
        readonly=True
    )
    
    month = fields.Selection(
        related='expense_id.month',
        string='Mes',
        store=True,
        readonly=True
    )
    
    year = fields.Integer(
        related='expense_id.year',
        string='Año',
        store=True,
        readonly=True
    )
    
    farmacia_id = fields.Many2one(
        'sindicato.proveedor',
        string='Farmacia',
        required=True,
        domain=[('tipo', '=', 'farmacia'), ('activo', '=', True)],
        ondelete='restrict'
    )
    
    gasto_plan = fields.Float(
        string='Gasto Plan',
        default=0.0,
        help='Consumo con cobertura del plan'
    )
    
    gasto_venta_libre = fields.Float(
        string='Venta Libre',
        default=0.0,
        help='Consumo sin cobertura (venta libre)'
    )
    
    gasto_total = fields.Float(
        string='Total',
        compute='_compute_gasto_total',
        store=True
    )
    
    @api.depends('gasto_plan', 'gasto_venta_libre')
    def _compute_gasto_total(self):
        for line in self:
            line.gasto_total = line.gasto_plan + line.gasto_venta_libre
    
    ticket_ids = fields.One2many('pharmacy.ticket', 'expense_line_id', string='Tickets')

    _sql_constraints = [
        ('unique_expense_farmacia',
         'UNIQUE(expense_id, farmacia_id)',
         'Ya existe una línea para esta farmacia en este registro de gastos')
    ]


class PharmacyTicket(models.Model):
    _name = 'pharmacy.ticket'
    _description = 'Ticket de farmacia'
    _order = 'fecha desc'

    expense_line_id = fields.Many2one(
        'affiliate.pharmacy.expense.line',
        string='Línea de Gasto',
        required=True,
        ondelete='cascade'
    )
    affiliate_id = fields.Many2one(
        related='expense_line_id.affiliate_id',
        store=True
    )
    farmacia_id = fields.Many2one(
        related='expense_line_id.farmacia_id',
        store=True
    )

    numero_orden = fields.Integer(string='N° Orden')
    nombre_archivo = fields.Char(string='Apellido y Nombre (archivo)')
    fecha = fields.Date(string='Fecha Ticket')
    monto_receta = fields.Float(string='Bajo Receta', default=0.0)
    monto_venta_libre = fields.Float(string='Venta Libre', default=0.0)
    monto_total = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('monto_receta', 'monto_venta_libre')
    def _compute_total(self):
        for rec in self:
            rec.monto_total = rec.monto_receta + rec.monto_venta_libre
