# -*- coding: utf-8 -*-
from odoo import models, fields


class AffiliationPeriod(models.Model):
    _inherit = 'affiliation.affiliation_period'

    # Columnas del "Libro de Afiliaciones" (registro histórico de altas y
    # bajas): datos del afiliado en solo lectura para listar/exportar sin
    # abrir cada ficha.
    affiliate_full_name = fields.Char(
        related='affiliate_id.display_full_name',
        string='Apellido y Nombre', readonly=True)
    affiliate_dni = fields.Char(
        related='affiliate_id.personal_id',
        string='DNI', readonly=True)
    affiliate_birth_date = fields.Date(
        related='affiliate_id.birth_date',
        string='Fecha de Nacimiento', readonly=True)
