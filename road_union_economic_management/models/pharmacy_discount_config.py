# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Valores usados históricamente cuando no hay configuración cargada
DEFAULT_TOPE = 125000.0
DEFAULT_PORCENTAJE = 40.0


class PharmacyDiscountConfig(models.Model):
    _name = 'pharmacy.discount.config'
    _description = 'Configuración de descuento de farmacia (tope y porcentaje por vigencia)'
    _order = 'date_year desc, date_month desc'

    date_month = fields.Selection([
        ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'),
        ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
        ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
    ], string='Vigente desde (mes)', required=True)
    date_year = fields.Integer(string='Vigente desde (año)', required=True)
    tope = fields.Float(
        string='Tope', required=True,
        help='Monto máximo de gasto mensual acumulado sobre el que el '
             'sindicato cubre el porcentaje de descuento.')
    porcentaje = fields.Float(
        string='Porcentaje cubierto (%)', required=True, default=DEFAULT_PORCENTAJE,
        help='Porcentaje del gasto en plan que absorbe el sindicato.')

    _sql_constraints = [
        ('unique_month_year',
         'UNIQUE(date_month, date_year)',
         'Ya existe una configuración vigente desde ese mes y año.'),
    ]

    def name_get(self):
        return [(rec.id, "Desde %s/%s: tope %s, %s%%" % (
            rec.date_month, rec.date_year, rec.tope, rec.porcentaje)) for rec in self]

    @api.model
    def get_for_month(self, month, year):
        """Devuelve (tope, fracción) vigente para un mes/año dado.

        Toma la configuración más reciente cuyo inicio de vigencia sea
        anterior o igual al mes consultado. Si no hay ninguna, usa los
        valores históricos hardcodeados hasta ahora (125000, 40%).
        """
        year = int(year)
        candidates = self.search([('date_year', '<=', year)])
        candidates = candidates.filtered(
            lambda c: c.date_year < year or c.date_month <= month)
        if not candidates:
            return DEFAULT_TOPE, DEFAULT_PORCENTAJE / 100.0
        best = max(candidates, key=lambda c: (c.date_year, c.date_month))
        return best.tope, best.porcentaje / 100.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_affected_expenses()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('tope', 'porcentaje', 'date_month', 'date_year')):
            self._recompute_affected_expenses()
        return res

    def unlink(self):
        configs = [(c.date_month, c.date_year) for c in self]
        res = super().unlink()
        for month, year in configs:
            self._recompute_expenses_from(month, year)
        return res

    def _recompute_affected_expenses(self):
        for config in self:
            self._recompute_expenses_from(config.date_month, config.date_year)

    @api.model
    def _recompute_expenses_from(self, month, year):
        """Recalcula descuentos de los gastos desde la vigencia en adelante."""
        Expense = self.env['affiliate.pharmacy.expenses']
        expenses = Expense.search([('year', '>=', int(year))])
        expenses = expenses.filtered(
            lambda e: e.year > int(year) or e.month >= month)
        if expenses:
            # Mismo idioma que _recalculate_future_months: forzar el
            # recálculo de los almacenados y sincronizar las cuentas
            expenses._compute_descuento_realizado()
            expenses._compute_desc_afil()
            expenses._compute_disponible_40()
            expenses._sync_payment_account()
