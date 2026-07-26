# -*- coding: utf-8 -*-
import base64
from datetime import datetime
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import UserError

MONTH_SELECTION = [
    ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'), ('04', 'Abril'),
    ('05', 'Mayo'), ('06', 'Junio'), ('07', 'Julio'), ('08', 'Agosto'),
    ('09', 'Septiembre'), ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
]


def _digits(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def _parse_amount(value):
    """Montos de la Caja: pueden venir numéricos, '257587.49' o '5778,00'."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(' ', '')
    if not s or s == '-':
        return 0.0
    if ',' in s and '.' in s:
        # '1.234,56': punto miles, coma decimal
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


class CajaResponseImportWizard(models.TransientModel):
    _name = 'caja.response.import.wizard'
    _description = 'Importar respuesta de la Caja de Jubilaciones (descontado real)'

    state = fields.Selection([
        ('step1', 'Carga'),
        ('step2', 'Preview'),
        ('step3', 'Resultado'),
    ], default='step1')

    file_data = fields.Binary(string='Archivo Excel de la Caja', attachment=False)
    file_name = fields.Char(string='Nombre del archivo')

    # El período sale de la columna "Período" del archivo (p. ej. 202606);
    # queda editable por si hay que corregirlo.
    date_month = fields.Selection(MONTH_SELECTION, string='Mes')
    date_year = fields.Selection(
        selection=lambda self: [(str(y), str(y)) for y in
                                reversed(range(datetime.now().year - 5,
                                               datetime.now().year + 2))],
        string='Año')

    preview_line_ids = fields.One2many(
        'caja.response.import.preview', 'wizard_id', string='Preview')
    total_ok = fields.Integer(string='Para actualizar', readonly=True)
    total_sin_cuenta = fields.Integer(string='Sin cuenta del mes', readonly=True)
    total_confirmadas = fields.Integer(string='Cuenta confirmada (no se toca)', readonly=True)
    total_no_match = fields.Integer(string='Sin afiliado', readonly=True)
    total_descontado = fields.Float(string='Total descontado', readonly=True)

    result_message = fields.Text(string='Resultado', readonly=True)

    def action_parse_file(self):
        """Paso 1 -> 2: parsear el Excel de la Caja y armar el preview."""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Debe seleccionar el archivo Excel de la Caja.'))
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('La librería openpyxl no está instalada.'))

        wb = openpyxl.load_workbook(BytesIO(base64.b64decode(self.file_data)),
                                    data_only=True)
        ws = wb.active

        # Columnas: Período | Código AIL | Nro Transacción | Nro Operación |
        #           Beneficio | Nombre | Cuil | Descontado | Solicitado | Estado
        periodo = None
        by_cuil = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or all(v is None for v in row):
                continue
            cuil = _digits(row[6])
            if not cuil:
                continue
            periodo = periodo or _digits(row[0])
            entry = by_cuil.setdefault(cuil, {
                'nombre': str(row[5] or '').strip(),
                'descontado': 0.0,
                'solicitado': 0.0,
            })
            # Un afiliado puede venir en varias filas (códigos AIL 1990/1991):
            # se suman
            entry['descontado'] += _parse_amount(row[7])
            entry['solicitado'] += _parse_amount(row[8])

        if not by_cuil:
            raise UserError(_('No se encontraron filas con CUIL en el archivo.'))

        if periodo and len(periodo) == 6:
            self.date_year = periodo[:4]
            self.date_month = periodo[4:6]
        if not self.date_month or not self.date_year:
            raise UserError(_('No pude deducir el período del archivo; '
                              'seleccioná mes y año manualmente.'))

        Affiliate = self.env['affiliation.affiliate']
        Account = self.env['affiliate.payment_account']
        Preview = self.env['caja.response.import.preview']

        self.preview_line_ids.unlink()
        counters = {'ok': 0, 'sin_cuenta': 0, 'confirmada': 0, 'no_match': 0}
        total_descontado = 0.0
        for cuil, entry in by_cuil.items():
            affiliate = Affiliate.search(
                [('vat', 'in', [cuil, '%s-%s-%s' % (cuil[:2], cuil[2:10], cuil[10:])])],
                limit=1)
            if not affiliate:
                affiliate = Affiliate.search([('name', '=', entry['nombre'])], limit=1)
            account = affiliate and Account.search([
                ('affiliate_id', '=', affiliate.id),
                ('date_month', '=', self.date_month),
                ('date_year', '=', self.date_year),
            ], limit=1)

            if not affiliate:
                status = 'no_match'
            elif not account:
                status = 'sin_cuenta'
            elif account.state == 'confirmed':
                status = 'confirmada'
            else:
                status = 'ok'
                total_descontado += entry['descontado']
            counters[status] += 1

            Preview.create({
                'wizard_id': self.id,
                'cuil': cuil,
                'nombre_archivo': entry['nombre'],
                'affiliate_id': affiliate.id if affiliate else False,
                'account_id': account.id if account else False,
                'descontado': entry['descontado'],
                'solicitado': entry['solicitado'],
                'status': status,
            })

        self.write({
            'state': 'step2',
            'total_ok': counters['ok'],
            'total_sin_cuenta': counters['sin_cuenta'],
            'total_confirmadas': counters['confirmada'],
            'total_no_match': counters['no_match'],
            'total_descontado': total_descontado,
        })
        return self._reopen()

    def action_confirm_import(self):
        """Paso 2 -> 3: volcar lo descontado en CAJA DE JUBILACIONES.

        La diferencia solicitado-descontado no se toca: queda en el saldo
        final del mes y pasa como saldo inicial al mes siguiente (así lo
        maneja administración). La liquidación a proveedores tampoco cambia:
        se les paga lo solicitado.
        """
        self.ensure_one()
        updated = 0
        for line in self.preview_line_ids.filtered(lambda l: l.status == 'ok'):
            line.account_id.pension_fund = line.descontado
            updated += 1

        skipped = len(self.preview_line_ids) - updated
        self.write({
            'state': 'step3',
            'result_message': _(
                'Se actualizaron %(updated)s cuentas de %(month)s/%(year)s con lo '
                'descontado por la Caja.\n'
                'Omitidas: %(skipped)s (sin afiliado, sin cuenta del mes o cuenta '
                'confirmada).\n\n'
                'La diferencia entre lo solicitado y lo descontado queda en el '
                'saldo final y pasa al mes siguiente.'
            ) % {'updated': updated, 'month': self.date_month,
                 'year': self.date_year, 'skipped': skipped},
        })
        return self._reopen()

    def action_back(self):
        self.write({'state': 'step1'})
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class CajaResponseImportPreview(models.TransientModel):
    _name = 'caja.response.import.preview'
    _description = 'Línea de preview del import de la Caja'

    wizard_id = fields.Many2one('caja.response.import.wizard', required=True,
                                ondelete='cascade')
    cuil = fields.Char(string='CUIL')
    nombre_archivo = fields.Char(string='Nombre (archivo)')
    affiliate_id = fields.Many2one('affiliation.affiliate', string='Afiliado')
    account_id = fields.Many2one('affiliate.payment_account', string='Cuenta')
    descontado = fields.Float(string='Descontado')
    solicitado = fields.Float(string='Solicitado')
    diferencia = fields.Float(string='Diferencia', compute='_compute_diferencia')
    status = fields.Selection([
        ('ok', 'OK'),
        ('sin_cuenta', 'Sin cuenta del mes'),
        ('confirmada', 'Cuenta confirmada'),
        ('no_match', 'Sin afiliado'),
    ], string='Estado')

    @api.depends('descontado', 'solicitado')
    def _compute_diferencia(self):
        for line in self:
            line.diferencia = line.solicitado - line.descontado
