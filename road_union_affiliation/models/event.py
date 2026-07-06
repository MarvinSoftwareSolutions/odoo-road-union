# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AffiliationEvent(models.Model):
    _name = 'affiliation.event'
    _description = 'Evento del sindicato con registro de asistencia'
    _order = 'date desc'

    name = fields.Char(string='Nombre', required=True)
    event_type = fields.Selection([
        ('asamblea', 'Asamblea'),
        ('fiesta', 'Fiesta'),
        ('eleccion', 'Elección'),
        ('otro', 'Otro'),
    ], string='Tipo', required=True, default='asamblea')
    date = fields.Date(string='Fecha', required=True,
                       default=fields.Date.context_today)
    description = fields.Text(string='Descripción')

    # La búsqueda para agregar asistentes acepta nombre, legajo (uid) o DNI
    # gracias al _name_search del afiliado.
    attendee_ids = fields.Many2many(
        'affiliation.affiliate',
        'affiliation_event_attendee_rel',
        'event_id', 'affiliate_id',
        string='Asistentes')

    attendee_count = fields.Integer(
        string='Cantidad de asistentes',
        compute='_compute_attendee_count', store=True)

    @api.depends('attendee_ids')
    def _compute_attendee_count(self):
        for event in self:
            event.attendee_count = len(event.attendee_ids)
