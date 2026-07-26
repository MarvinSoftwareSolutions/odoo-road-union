# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime

MONTH_SELECTION = [
    ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
    ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
    ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
]

MONTH_SHORT = {
    '01': 'ene', '02': 'feb', '03': 'mar', '04': 'abr', '05': 'may', '06': 'jun',
    '07': 'jul', '08': 'ago', '09': 'sep', '10': 'oct', '11': 'nov', '12': 'dic',
}

MONTH_LONG = dict(MONTH_SELECTION)

# Conceptos de servicios del resumen económico (campo -> etiqueta).
# Solo se listan en el reporte los que tengan algún monto en el rango.
SERVICE_CONCEPTS = [
    ('pharmacy_total', 'Farmacia'),
    ('optical_total', 'Óptica'),
    ('punilla_total', 'Punilla'),
    ('solar', 'Solar'),
    ('caruso', 'Caruso'),
    ('parque_del_sol', 'Parque del Sol'),
    ('salguero', 'Salguero'),
    ('tres_provincias', 'Tres Provincias'),
    ('ecco_loan', 'ECCO'),
    ('emi_loan', 'EMI'),
    ('emergency_loan', 'Urgencias'),
    ('suoem_loan', 'SUOEM'),
    ('tourism_total', 'Turismo'),
    ('aid_total', 'Ayuda Solidaria'),
    ('party_total', 'Fiesta'),
    ('hall_total', 'Salón'),
    ('odontology_total', 'Odontología'),
    ('collections_total', 'Colectas'),
    ('otros_1', 'Otros 1'),
    ('otros_2', 'Otros 2'),
]


class AffiliateSummaryReportWizard(models.TransientModel):
    _name = 'affiliate.summary.report.wizard'
    _description = 'Detalle económico multi-mes por afiliado'

    affiliate_id = fields.Many2one(
        'affiliation.affiliate', string='Afiliado', required=True)

    from_month = fields.Selection(MONTH_SELECTION, string='Desde (mes)', required=True)
    from_year = fields.Integer(string='Desde (año)', required=True)
    to_month = fields.Selection(MONTH_SELECTION, string='Hasta (mes)', required=True)
    to_year = fields.Integer(string='Hasta (año)', required=True)
    include_pharmacy_detail = fields.Boolean(
        string='Incluir detalle de farmacia', default=True,
        help='Agrega al pie el detalle de tickets de farmacia de cada mes.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Por defecto: el año calendario completo (así entrega la
        # administración el detalle al afiliado; los meses sin datos
        # se muestran vacíos)
        year = datetime.today().year
        res.update({
            'from_month': '01',
            'from_year': year,
            'to_month': '12',
            'to_year': year,
        })
        return res

    def action_print(self):
        self.ensure_one()
        data = {
            # El cliente web no manda docids en la URL cuando la acción de
            # reporte lleva data: los ids viajan acá y el AbstractModel los
            # toma como fallback.
            'ids': self.affiliate_id.ids,
            'from_month': self.from_month,
            'from_year': self.from_year,
            'to_month': self.to_month,
            'to_year': self.to_year,
            'include_pharmacy_detail': self.include_pharmacy_detail,
        }
        report = self.env.ref(
            'road_union_economic_management.action_report_affiliate_multi_month')
        return report.report_action(self.affiliate_id, data=data)


class ReportAffiliateMultiMonth(models.AbstractModel):
    _name = 'report.road_union_economic_management.report_multi_month'
    _description = 'Detalle económico multi-mes por afiliado (QWeb)'

    @staticmethod
    def _month_range(from_month, from_year, to_month, to_year):
        """Lista de (mes '01'..'12', año int) desde-hasta inclusive."""
        months = []
        m, y = int(from_month), int(from_year)
        end = (int(to_year), int(to_month))
        while (y, m) <= end and len(months) < 36:  # tope de sanidad: 3 años
            months.append(('%02d' % m, y))
            m += 1
            if m > 12:
                m, y = 1, y + 1
        return months

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        docids = docids or data.get('ids') or data.get(
            'context', {}).get('active_ids', [])
        affiliate = self.env['affiliation.affiliate'].browse(docids)[:1]
        months = self._month_range(
            data.get('from_month', '01'), data.get('from_year', datetime.today().year),
            data.get('to_month', '12'), data.get('to_year', datetime.today().year))

        Pay = self.env['affiliate.payment_account']
        accounts = []
        for m, y in months:
            accounts.append(Pay.search([
                ('affiliate_id', '=', affiliate.id),
                ('date_month', '=', m),
                ('date_year', '=', str(y)),
            ], limit=1))

        def row(field):
            return [acc and acc[field] or 0.0 for acc in accounts]

        service_rows = []
        for field, label in SERVICE_CONCEPTS:
            vals = row(field)
            if any(vals):
                service_rows.append({'label': label, 'vals': vals})

        summary_rows = [
            {'label': 'SALDO ANTERIOR', 'vals': row('initial_balance'), 'bold': False},
            {'label': 'Cuota Sindical', 'vals': row('union_fee'), 'bold': False},
            {'label': 'TOTAL A DESCONTAR', 'vals': row('total'), 'bold': True},
            {'label': 'PAGO', 'vals': row('payments'), 'bold': True},
        ]
        for field, label in [('meta4', 'META 4'),
                             ('pension_fund', 'CAJA DE JUBILACIONES')]:
            vals = row(field)
            if any(vals):
                summary_rows.append({'label': label, 'vals': vals, 'bold': False})
        summary_rows.append(
            {'label': 'SALDO FINAL', 'vals': row('final_balance'), 'bold': True})

        pharmacy_sections = []
        if data.get('include_pharmacy_detail'):
            Expense = self.env['affiliate.pharmacy.expenses']
            for m, y in months:
                expense = Expense.search([
                    ('affiliate_id', '=', affiliate.id),
                    ('month', '=', m),
                    ('year', '=', y),
                ], limit=1)
                if not expense:
                    continue
                tickets = []
                for line in expense.linea_gastos_ids:
                    for ticket in line.ticket_ids:
                        tickets.append({
                            'fecha': ticket.fecha,
                            'receta': ticket.monto_receta,
                            'venta_libre': ticket.monto_venta_libre,
                            'total': ticket.monto_total,
                            'farmacia': line.farmacia_id.nombre,
                        })
                if not tickets and not expense.suma_mes:
                    continue
                pharmacy_sections.append({
                    'label': 'FCIA %s %s' % (MONTH_LONG[m].upper(), y),
                    'tickets': tickets,
                    'descuento': expense.descuento_realizado,
                    'total_descontar': expense.desc_afil,
                })

        return {
            'doc_ids': docids,
            'doc_model': 'affiliation.affiliate',
            'docs': affiliate,
            'doc': affiliate,
            'month_labels': ['%s-%s' % (MONTH_SHORT[m], str(y)[2:]) for m, y in months],
            'service_rows': service_rows,
            'summary_rows': summary_rows,
            'pharmacy_sections': pharmacy_sections,
            'fmt': lambda v: ('{:,.2f}'.format(v)
                              .replace(',', '@').replace('.', ',').replace('@', '.')) if v else '-',
        }
