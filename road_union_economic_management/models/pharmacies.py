# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

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
    '12': ('01', 1),  # Diciembre (12) -> Enero (1) del año siguiente (+1)
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

    gasto_farmacia1 = fields.Float(string="Estrella")
    gasto_farmacia1_vl = fields.Float(string="Estrella V.L.")
    gasto_farmacia2 = fields.Float(string="Nueva Cba")
    gasto_farmacia2_vl = fields.Float(string="Nueva Cba V.L.")
    gasto_farmacia3 = fields.Float(string="General Paz")
    gasto_farmacia3_vl = fields.Float(string="General Paz V.L.")
    gasto_farmacia4 = fields.Float(string="Medicarlo")
    gasto_farmacia4_vl = fields.Float(string="Medicarlo V.L.")
    gasto_farmacia5 = fields.Float(string="Farmavida")
    gasto_farmacia5_vl = fields.Float(string="Farmavida V.L.")
    gasto_farmacia6 = fields.Float(string="Del Indio")
    gasto_farmacia6_vl = fields.Float(string="Del Indio V.L.")

    suma_mes = fields.Float(string="Suma Mes", compute="_compute_total", store=True)
    
    vta_libre = fields.Float(string="VTA LIBRE", compute="_compute_vta_libre", store=True)
    
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

    @api.depends(
        "gasto_farmacia1", "gasto_farmacia2", "gasto_farmacia3", 
        "gasto_farmacia4", "gasto_farmacia5", "gasto_farmacia6",
    )
    def _compute_total(self):
        for rec in self:
            rec.suma_mes = (
                rec.gasto_farmacia1 + 
                rec.gasto_farmacia2 + 
                rec.gasto_farmacia3 +
                rec.gasto_farmacia4 + 
                rec.gasto_farmacia5 + 
                rec.gasto_farmacia6 
            )

    @api.depends(
        "gasto_farmacia1_vl", "gasto_farmacia2_vl", "gasto_farmacia3_vl",
        "gasto_farmacia4_vl", "gasto_farmacia5_vl", "gasto_farmacia6_vl",
    )
    def _compute_vta_libre(self):
        for rec in self:
            rec.vta_libre = (
                rec.gasto_farmacia1_vl +
                rec.gasto_farmacia2_vl +
                rec.gasto_farmacia3_vl +
                rec.gasto_farmacia4_vl +
                rec.gasto_farmacia5_vl +
                rec.gasto_farmacia6_vl
            )

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

    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribimos create para recalcular meses posteriores"""
        records = super(AffiliatePharmacyExpenses, self).create(vals_list)
        for record in records:
            record._recalculate_future_months()
        return records

    def write(self, vals):
        """Sobrescribimos write para recalcular meses posteriores"""
        res = super(AffiliatePharmacyExpenses, self).write(vals)
        # Solo recalculamos si cambiaron campos que afectan los totales
        if any(field in vals for field in ['gasto_farmacia1', 'gasto_farmacia2', 'gasto_farmacia3',
                                            'gasto_farmacia4', 'gasto_farmacia5', 'gasto_farmacia6',
                                            'month', 'year', 'affiliate_id']):
            for record in self:
                record._recalculate_future_months()
        return res

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