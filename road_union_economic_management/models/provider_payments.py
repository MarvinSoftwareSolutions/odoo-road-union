# -*- coding: utf-8 -*-
import base64
import io

import xlsxwriter

from odoo import models, fields, api

class ProveedorSindicato(models.Model):
    _name = 'sindicato.proveedor'
    _description = 'Proveedor del Sindicato'
    _rec_name = 'nombre'

    nombre = fields.Char(string='Nombre', required=True)
    tipo = fields.Selection([
        ('farmacia', 'Farmacia'),
        ('otro', 'Otro')
    ], string='Tipo', required=True, default='otro')
    porcentaje_comision = fields.Float(
        string='Porcentaje de Comisión (%)',
        required=True,
        help='Porcentaje entre 0 y 100'
    )
    activo = fields.Boolean(string='Activo', default=True)
    
    importe_ids = fields.One2many(
        'sindicato.importe.mensual',
        'proveedor_id',
        string='Importes Mensuales'
    )

    @api.constrains('porcentaje_comision')
    def _check_porcentaje(self):
        for record in self:
            if record.porcentaje_comision < 0 or record.porcentaje_comision > 100:
                raise models.ValidationError(
                    'El porcentaje de comisión debe estar entre 0 y 100'
                )

    def _invalidar_cache_vistas_gastos(self):
        """Invalida el caché de vistas cuando cambian las farmacias"""
        # Verificar si el modelo existe antes de limpiar su caché
        if 'sindicato.gasto.farmacia.linea' in self.env:
            self.env['sindicato.gasto.farmacia.linea'].clear_caches()
        
        # Limpiar caché del registro en ir.ui.view
        self.env['ir.ui.view'].clear_caches()
    
    @api.model_create_multi
    def create(self, vals_list):
        """Sobrescribir create para invalidar caché cuando se crea una farmacia"""
        records = super().create(vals_list)
        
        # Verificar si alguno de los registros creados es una farmacia activa
        if any(r.tipo == 'farmacia' and r.activo for r in records):
            self._invalidar_cache_vistas_gastos()
        
        return records
    
    def write(self, vals):
        """Sobrescribir write para invalidar caché cuando se modifica una farmacia"""
        result = super().write(vals)
        
        # Si se modificó el estado activo o el tipo, invalidar caché
        if 'activo' in vals or 'tipo' in vals:
            if any(r.tipo == 'farmacia' for r in self):
                self._invalidar_cache_vistas_gastos()
        
        return result
    
    def unlink(self):
        """Sobrescribir unlink para invalidar caché cuando se elimina una farmacia"""
        # Verificar antes de eliminar si hay farmacias
        tiene_farmacias = any(r.tipo == 'farmacia' and r.activo for r in self)
        
        result = super().unlink()
        
        if tiene_farmacias:
            self._invalidar_cache_vistas_gastos()
        
        return result


class LiquidacionMensual(models.Model):
    _name = 'sindicato.liquidacion.mensual'
    _description = 'Liquidación Mensual'
    _rec_name = 'descripcion'
    _order = 'anio desc, mes desc'

    mes = fields.Integer(
        string='Mes',
        required=True,
        default=lambda self: fields.Date.today().month
    )
    
    anio = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: fields.Date.today().year
    )
    
    descripcion = fields.Char(
        string='Descripción',
        compute='_compute_descripcion',
        store=True
    )
    
    importe_ids = fields.One2many(
        'sindicato.importe.mensual',
        'liquidacion_id',
        string='Importes por Proveedor'
    )
    
    total_importe_plan = fields.Monetary(
        string='Total Importe Plan',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id'
    )
    
    total_comision = fields.Monetary(
        string='Total Comisión',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id'
    )
    
    total_importe_pagar = fields.Monetary(
        string='Total Importe a Pagar',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id'
    )
    
    total_farmacias = fields.Monetary(
        string='Total 40% Farmacias',
        compute='_compute_totales',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )

    observaciones = fields.Text(
        string='Observaciones',
        help='Aclaraciones internas de administración (van al pie de la '
             'planilla impresa y del Excel).'
    )

    @api.depends('mes', 'anio')
    def _compute_descripcion(self):
        meses = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }
        for record in self:
            if record.mes and record.anio:
                record.descripcion = f"{meses.get(record.mes, '')} {record.anio}"
            else:
                record.descripcion = 'Nueva Liquidación'
    
    @api.depends('importe_ids.importe_total_plan', 'importe_ids.comision',
                 'importe_ids.importe_a_pagar', 'importe_ids.cuarenta_porciento_farmacias')
    def _compute_totales(self):
        for record in self:
            record.total_importe_plan = sum(record.importe_ids.mapped('importe_total_plan'))
            record.total_comision = sum(record.importe_ids.mapped('comision'))
            record.total_importe_pagar = sum(record.importe_ids.mapped('importe_a_pagar'))
            record.total_farmacias = sum(record.importe_ids.mapped('cuarenta_porciento_farmacias'))
    
    def action_generar_lineas(self):
        """Genera líneas para todos los proveedores activos que no tengan importe"""
        self.ensure_one()
        
        proveedores = self.env['sindicato.proveedor'].search([('activo', '=', True)])
        proveedores_existentes = self.importe_ids.mapped('proveedor_id')
        
        for proveedor in proveedores:
            if proveedor not in proveedores_existentes:
                self.env['sindicato.importe.mensual'].create({
                    'liquidacion_id': self.id,
                    'proveedor_id': proveedor.id,
                    'mes': self.mes,
                    'anio': self.anio,
                    'importe_total_plan': 0.0,
                })
        
        return True
    
    def action_calcular_farmacias_desde_gastos(self):
        """Completa las líneas de farmacia desde los gastos cargados del mes.

        Para cada farmacia de la liquidación:
        - importe_total_plan = todo lo presentado ese mes (plan + venta libre)
        - 40% farmacias = parte del descuento absorbido por el sindicato
          atribuible a esa farmacia (proporcional al gasto de plan de cada
          afiliado, ya que el descuento se calcula por afiliado sobre el
          total de sus farmacias).

        Los valores quedan editables: el cálculo es un punto de partida.
        """
        self.ensure_one()
        month = '%02d' % self.mes
        lines = self.env['affiliate.pharmacy.expense.line'].search([
            ('month', '=', month),
            ('year', '=', self.anio),
        ])
        for importe in self.importe_ids.filtered('es_farmacia'):
            flines = lines.filtered(
                lambda l, prov=importe.proveedor_id: l.farmacia_id == prov)
            total = sum(flines.mapped('gasto_total'))
            subsidio = 0.0
            for line in flines:
                expense = line.expense_id
                if expense.suma_mes:
                    subsidio += expense.descuento_realizado * (
                        line.gasto_plan / expense.suma_mes)
            importe.write({
                'importe_total_plan': total,
                'cuarenta_porciento_farmacias': subsidio,
            })
        return True

    def action_exportar_excel(self):
        """Genera la planilla de pagos en Excel (formato del modelo de
        administración: proveedor, %, comisión, importe, a pagar,
        40% farmacias, Nº transferencia + totales + observaciones)."""
        self.ensure_one()
        buf = io.BytesIO()
        workbook = xlsxwriter.Workbook(buf, {'in_memory': True})
        sheet = workbook.add_worksheet((self.descripcion or 'Planilla')[:31])
        bold = workbook.add_format({'bold': True})
        header = workbook.add_format({'bold': True, 'bottom': 2})
        money = workbook.add_format({'num_format': '#,##0.00'})
        money_bold = workbook.add_format({'num_format': '#,##0.00', 'bold': True})

        sheet.set_column(0, 0, 38)
        sheet.set_column(1, 6, 16)
        sheet.write(0, 0, 'PLANILLA DE PAGOS A PROVEEDORES', bold)
        sheet.write(1, 0, 'Período: %s' % (self.descripcion or ''))

        headers = ['Proveedor', '% Comisión', 'Comisión', 'Importe Total del Plan',
                   'Importe a Pagar', '40% Farmacias', 'Nº Transferencia']
        row = 3
        for col, title in enumerate(headers):
            sheet.write(row, col, title, header)

        for line in self.importe_ids:
            if not line.importe_total_plan and not line.cuarenta_porciento_farmacias:
                continue
            row += 1
            sheet.write(row, 0, line.proveedor_id.nombre or '')
            sheet.write_number(row, 1, line.porcentaje_comision or 0)
            sheet.write_number(row, 2, line.comision or 0, money)
            sheet.write_number(row, 3, line.importe_total_plan or 0, money)
            sheet.write_number(row, 4, line.importe_a_pagar or 0, money)
            sheet.write_number(row, 5, line.cuarenta_porciento_farmacias or 0, money)
            sheet.write(row, 6, line.nro_transferencia or '')

        row += 1
        sheet.write(row, 0, 'TOTALES', bold)
        sheet.write_number(row, 2, self.total_comision or 0, money_bold)
        sheet.write_number(row, 3, self.total_importe_plan or 0, money_bold)
        sheet.write_number(row, 4, self.total_importe_pagar or 0, money_bold)
        sheet.write_number(row, 5, self.total_farmacias or 0, money_bold)

        if self.observaciones:
            sheet.write(row + 2, 0, 'Observaciones:', bold)
            sheet.write(row + 3, 0, self.observaciones)

        workbook.close()
        filename = 'Planilla de Pagos %s.xlsx' % (self.descripcion or '')
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(buf.getvalue()),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % attachment.id,
            'target': 'self',
        }

    @api.model
    def get_or_create_current_month(self):
        """Obtiene o crea la liquidación del mes actual"""
        today = fields.Date.today()
        mes_actual = today.month
        anio_actual = today.year
        
        liquidacion = self.search([
            ('mes', '=', mes_actual),
            ('anio', '=', anio_actual)
        ], limit=1)
        
        if not liquidacion:
            liquidacion = self.create({
                'mes': mes_actual,
                'anio': anio_actual,
            })
            liquidacion.action_generar_lineas()
        
        return liquidacion
    
    _sql_constraints = [
        ('unique_mes_anio',
         'UNIQUE(mes, anio)',
         'Ya existe una liquidación para este mes y año')
    ]


class ImporteMensualProveedor(models.Model):
    _name = 'sindicato.importe.mensual'
    _description = 'Importe Mensual por Proveedor'
    _rec_name = 'descripcion'
    _order = 'proveedor_id'

    liquidacion_id = fields.Many2one(
        'sindicato.liquidacion.mensual',
        string='Liquidación',
        required=True,
        ondelete='cascade'
    )
    
    proveedor_id = fields.Many2one(
        'sindicato.proveedor',
        string='Proveedor',
        required=True,
        ondelete='restrict'
    )
    
    mes = fields.Integer(
        string='Mes',
        related='liquidacion_id.mes',
        store=True,
        readonly=True
    )
    
    anio = fields.Integer(
        string='Año',
        related='liquidacion_id.anio',
        store=True,
        readonly=True
    )
    
    importe_total_plan = fields.Monetary(
        string='Importe Total del Plan',
        currency_field='currency_id',
        default=0.0
    )
    
    porcentaje_comision = fields.Float(
        string='Porcentaje (%)',
        related='proveedor_id.porcentaje_comision',
        store=True,
        readonly=True
    )
    
    comision = fields.Monetary(
        string='Comisión',
        compute='_compute_importes',
        store=True,
        currency_field='currency_id'
    )
    
    importe_a_pagar = fields.Monetary(
        string='Importe a Pagar',
        compute='_compute_importes',
        store=True,
        currency_field='currency_id'
    )
    
    es_farmacia = fields.Boolean(
        string='Es Farmacia',
        compute='_compute_es_farmacia',
        store=True
    )
    
    cuarenta_porciento_farmacias = fields.Monetary(
        string='40% Farmacias',
        currency_field='currency_id',
        default=0.0,
        help='Campo manual para farmacias'
    )

    nro_transferencia = fields.Char(
        string='Nº Transferencia',
        help='Número de la transferencia bancaria con la que se pagó'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id
    )
    
    descripcion = fields.Char(
        string='Descripción',
        compute='_compute_descripcion',
        store=True
    )
    
    @api.depends('proveedor_id.tipo')
    def _compute_es_farmacia(self):
        for record in self:
            record.es_farmacia = record.proveedor_id.tipo == 'farmacia'
    
    @api.depends('importe_total_plan', 'porcentaje_comision')
    def _compute_importes(self):
        for record in self:
            if record.importe_total_plan and record.porcentaje_comision:
                record.comision = record.importe_total_plan * (record.porcentaje_comision / 100)
                record.importe_a_pagar = record.importe_total_plan - record.comision
            else:
                record.comision = 0
                record.importe_a_pagar = record.importe_total_plan
    
    @api.depends('proveedor_id', 'mes', 'anio')
    def _compute_descripcion(self):
        for record in self:
            if record.proveedor_id and record.mes and record.anio:
                record.descripcion = f"{record.proveedor_id.nombre} - {record.mes:02d}/{record.anio}"
            else:
                record.descripcion = 'Nuevo'
    
    _sql_constraints = [
        ('unique_proveedor_liquidacion',
         'UNIQUE(proveedor_id, liquidacion_id)',
         'Ya existe un registro para este proveedor en esta liquidación')
    ]