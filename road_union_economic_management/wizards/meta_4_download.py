from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from datetime import datetime, date, timedelta
import unicodedata

class PaymentExportWizard(models.TransientModel):
    _name = 'payment.export.wizard'
    _description = 'Wizard para exportar archivos TXT'

    date_month = fields.Selection(
        selection=[
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
        ],
        string='Mes',
        required=True,
        default=lambda self: datetime.now().strftime('%m')
    )

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in
                reversed(range(current_year - 5, current_year + 2))]

    date_year = fields.Selection(
        selection=_get_year_selection,
        string='Año',
        required=True,
        default=lambda self: str(datetime.now().year)
    )

    # Archivos individuales
    file_data_payments = fields.Binary(string='Archivo Pagos', readonly=True)
    file_name_payments = fields.Char(string='Nombre archivo pagos', readonly=True)
    
    file_data_affiliations = fields.Binary(string='Archivo Altas/Bajas', readonly=True)
    file_name_affiliations = fields.Char(string='Nombre archivo altas/bajas', readonly=True)
    
    file_data_union_fees = fields.Binary(string='Archivo Cuotas', readonly=True)
    file_name_union_fees = fields.Char(string='Nombre archivo cuotas', readonly=True)
    
    state = fields.Selection([
        ('step1', 'Configuración'),
        ('step2', 'Archivos generados')
    ], default='step1')

    total_records_payments = fields.Integer(string='Registros de pagos', readonly=True)
    total_records_affiliations = fields.Integer(string='Registros de altas/bajas', readonly=True)
    total_records_union_fees = fields.Integer(string='Registros de cuotas sindicales', readonly=True)
    
    def _get_date_range(self):
        """Obtiene el rango de fechas del mes/año seleccionado"""
        year = int(self.date_year)
        month = int(self.date_month)
        
        # Primer día del mes
        start_date = date(year, month, 1)
        
        # Último día del mes
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        return start_date, end_date
    
    def _format_day_without_leading_zero(self, date_field):
        """Formatea el día removiendo el 0 inicial si existe"""
        day = date_field.strftime('%d')
        return str(int(day))  # Esto remueve el 0 inicial automáticamente
    
    def _generate_payments_file(self):
        """Genera el archivo de pagos (7281)"""
        payment_accounts = self.env['affiliate.payment_account'].search([
            ('date_month', '=', self.date_month),
            ('date_year', '=', self.date_year),
            ('affiliate_id.affiliate_type_id.name', '=', 'Activo'),
        ])
        
        file_content = ""
        processed_records = 0
        
        # Crear fecha en formato YYYYMMDD (día 25 del mes seleccionado)
        date_str = f"{self.date_year}{self.date_month}25"
        
        for payment in payment_accounts:
            if not payment.affiliate_id.id_benefit:
                continue
                
            # Calcular: Total Servicios - Pagos
            amount = payment.total_services - payment.payments
            
            # Formatear el monto
            if amount == int(amount):
                amount_str = str(int(amount))
            else:
                amount_str = f"{amount:.2f}".replace('.', ',')
            
            # Crear línea: ID_BENEFIT    7281  AMOUNT    DATE
            line = f"{payment.affiliate_id.id_benefit}    7281  {amount_str}                                             {date_str}\n"
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"7281{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def _format_fixed_width_line(self, pe, id_benefit, day, concept, value, action, last_name, first_name, imputation_date):
        """Formatea una línea con anchos fijos"""
        # Anchos definidos:
        # PE: 2, ID_BENEFIT: 9, DIA: 4, CONCEPTO: 6, VALOR: 14, ACCION: 2, APELLIDO: 40, NOMBRE: 40, FECHA: 8
        
        pe_formatted = str(pe).ljust(2)[:2]
        id_benefit_formatted = str(id_benefit).ljust(9)[:9]
        day_formatted = str(day).ljust(4)[:4]
        concept_formatted = str(concept).ljust(6)[:6]
        value_formatted = str(value).ljust(14)[:14]
        action_formatted = str(action).ljust(2)[:2]
        last_name_formatted = str(self._clean_text(last_name)).ljust(40)[:40]
        first_name_formatted = str(self._clean_text(first_name)).ljust(40)[:40]
        date_formatted = str(imputation_date).ljust(8)[:8]
        
        return f"{pe_formatted}{id_benefit_formatted}{day_formatted}{concept_formatted}{value_formatted}{action_formatted}{last_name_formatted}{first_name_formatted}{date_formatted}\n"

    def _clean_text(self, text):
        """Convierte texto a mayúsculas y remueve caracteres especiales (tildes) pero mantiene las ñ"""
        if not text:
            return ''
        
        # Convertir a mayúsculas
        text = str(text).upper()
        
        # Remover tildes y caracteres especiales pero preservar Ñ
        # Normalizar usando NFD (descomponer caracteres con tildes)
        text = unicodedata.normalize('NFD', text)
        
        # Filtrar solo caracteres ASCII más la Ñ (esto remueve las tildes pero mantiene la Ñ)
        cleaned_chars = []
        for char in text:
            if unicodedata.category(char) != 'Mn':  # No es una marca diacrítica
                cleaned_chars.append(char)
        
        text = ''.join(cleaned_chars)
        
        # Reemplazos específicos para otros caracteres especiales (sin incluir Ñ)
        replacements = {
            'Ü': 'U',
            'Ç': 'C'
        }
        
        for original, replacement in replacements.items():
            text = text.replace(original, replacement)
        
        return text

    def _generate_affiliations_file(self):
        """Genera el archivo de altas/bajas (8522)"""
        start_date, end_date = self._get_date_range()
        
        file_content = ""
        processed_records = 0
        
        # Fecha de imputación en formato YYYYMMDD (día 25 del mes seleccionado)
        imputation_date = f"{self.date_year}{self.date_month}25"
        
        # Buscar afiliaciones en el mes (solo afiliados activos)
        affiliations = self.env['affiliation.affiliate'].search([
            ('affiliation_date', '>=', start_date),
            ('affiliation_date', '<=', end_date),
            ('id_benefit', '!=', False),
            ('affiliate_type_id.name', '=', 'Activo'),
        ])
        
        for affiliate in affiliations:
            if not affiliate.id_benefit:
                continue
                
            # Obtener el día sin 0 inicial
            day = self._format_day_without_leading_zero(affiliate.affiliation_date)
            
            # Crear línea para alta (acción 00)
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, '8522', '', '00',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        # Buscar desafiliaciones en el mes (incluir todos los que se desafiliaron, independiente del estado actual)
        disaffiliations = self.env['affiliation.affiliate'].search([
            ('disaffiliation_date', '>=', start_date),
            ('disaffiliation_date', '<=', end_date),
            ('id_benefit', '!=', False),
        ])
        
        for affiliate in disaffiliations:
            if not affiliate.id_benefit:
                continue
                
            # Obtener el día sin 0 inicial
            day = self._format_day_without_leading_zero(affiliate.disaffiliation_date)
            
            # Crear línea para baja (acción 99)
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, '8522', '', '99',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"8522{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def _generate_union_fees_file(self):
        """Genera el archivo de cuotas sindicales (828)"""
        payment_accounts = self.env['affiliate.payment_account'].search([
            ('date_month', '=', self.date_month),
            ('date_year', '=', self.date_year),
            ('affiliate_id.affiliate_type_id.name', '=', 'Activo'),
            # Incluir registros con union_fee = 0 también
        ])
        
        file_content = ""
        processed_records = 0
        
        # Fecha de imputación en formato YYYYMMDD (día 25 del mes seleccionado)
        imputation_date = f"{self.date_year}{self.date_month}25"
        
        for payment in payment_accounts:
            affiliate = payment.affiliate_id
            if not affiliate.id_benefit or not affiliate.affiliation_date:
                continue
            
            # Obtener el día sin 0 inicial
            day = self._format_day_without_leading_zero(affiliate.affiliation_date)
            
            # Formatear el valor de la cuota sindical
            union_fee = payment.union_fee or 0  # Incluir 0 también
            if union_fee == int(union_fee):
                fee_str = str(int(union_fee))
            else:
                fee_str = f"{union_fee:.2f}".replace('.', ',')
            
            # Crear línea con formato fijo
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, '828', fee_str, '00',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"828{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def action_generate_payments(self):
        """Genera solo el archivo de pagos"""
        payments_content, payments_name, payments_count = self._generate_payments_file()
        
        if payments_count == 0:
            raise UserError(f'No se encontraron registros de pagos para el período {self.date_month}/{self.date_year}.')
        
        payments_data = base64.b64encode(payments_content.encode('utf-8'))
        
        self.write({
            'file_data_payments': payments_data,
            'file_name_payments': payments_name,
            'state': 'step2',
            'total_records_payments': payments_count,
            'total_records_affiliations': 0,
            'total_records_union_fees': 0
        })
        
        return self._return_to_wizard()
    
    def action_generate_affiliations(self):
        """Genera solo el archivo de altas/bajas"""
        affiliations_content, affiliations_name, affiliations_count = self._generate_affiliations_file()
        
        if affiliations_count == 0:
            raise UserError(f'No se encontraron registros de altas/bajas para el período {self.date_month}/{self.date_year}.')
        
        affiliations_data = base64.b64encode(affiliations_content.encode('utf-8'))
        
        self.write({
            'file_data_affiliations': affiliations_data,
            'file_name_affiliations': affiliations_name,
            'state': 'step2',
            'total_records_payments': 0,
            'total_records_affiliations': affiliations_count,
            'total_records_union_fees': 0
        })
        
        return self._return_to_wizard()
    
    def action_generate_union_fees(self):
        """Genera solo el archivo de cuotas sindicales"""
        union_fees_content, union_fees_name, union_fees_count = self._generate_union_fees_file()
        
        if union_fees_count == 0:
            raise UserError(f'No se encontraron registros de cuotas sindicales para el período {self.date_month}/{self.date_year}.')
        
        union_fees_data = base64.b64encode(union_fees_content.encode('utf-8'))
        
        self.write({
            'file_data_union_fees': union_fees_data,
            'file_name_union_fees': union_fees_name,
            'state': 'step2',
            'total_records_payments': 0,
            'total_records_affiliations': 0,
            'total_records_union_fees': union_fees_count
        })
        
        return self._return_to_wizard()
    
    def action_generate_all(self):
        """Genera los tres archivos"""
        # Generar cada archivo
        payments_content, payments_name, payments_count = self._generate_payments_file()
        affiliations_content, affiliations_name, affiliations_count = self._generate_affiliations_file()
        union_fees_content, union_fees_name, union_fees_count = self._generate_union_fees_file()
        
        # Verificar que al menos un archivo tenga contenido
        if payments_count == 0 and affiliations_count == 0 and union_fees_count == 0:
            raise UserError(f'No se encontraron registros para generar archivos del período {self.date_month}/{self.date_year}.')
        
        # Codificar archivos individuales
        payments_data = base64.b64encode(payments_content.encode('utf-8')) if payments_count > 0 else False
        affiliations_data = base64.b64encode(affiliations_content.encode('utf-8')) if affiliations_count > 0 else False
        union_fees_data = base64.b64encode(union_fees_content.encode('utf-8')) if union_fees_count > 0 else False
        
        # Actualizar wizard
        self.write({
            'file_data_payments': payments_data,
            'file_name_payments': payments_name if payments_count > 0 else False,
            'file_data_affiliations': affiliations_data,
            'file_name_affiliations': affiliations_name if affiliations_count > 0 else False,
            'file_data_union_fees': union_fees_data,
            'file_name_union_fees': union_fees_name if union_fees_count > 0 else False,
            'state': 'step2',
            'total_records_payments': payments_count,
            'total_records_affiliations': affiliations_count,
            'total_records_union_fees': union_fees_count
        })
        
        return self._return_to_wizard()
    
    def _return_to_wizard(self):
        """Método auxiliar para retornar al wizard"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }
    
    def action_download_payments(self):
        """Descarga el archivo de pagos"""
        if not self.file_data_payments:
            raise UserError('No hay archivo de pagos para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data_payments&download=true&filename={self.file_name_payments}',
            'target': 'self',
        }
    
    def action_download_affiliations(self):
        """Descarga el archivo de altas/bajas"""
        if not self.file_data_affiliations:
            raise UserError('No hay archivo de altas/bajas para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data_affiliations&download=true&filename={self.file_name_affiliations}',
            'target': 'self',
        }
    
    def action_download_union_fees(self):
        """Descarga el archivo de cuotas sindicales"""
        if not self.file_data_union_fees:
            raise UserError('No hay archivo de cuotas sindicales para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data_union_fees&download=true&filename={self.file_name_union_fees}',
            'target': 'self',
        }
    
    def action_back(self):
        """Volver al paso anterior"""
        self.write({
            'state': 'step1',
            'file_data_payments': False,
            'file_name_payments': False,
            'file_data_affiliations': False,
            'file_name_affiliations': False,
            'file_data_union_fees': False,
            'file_name_union_fees': False,
            'total_records_payments': 0,
            'total_records_affiliations': 0,
            'total_records_union_fees': 0
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.export.wizard',
            'view_mode': 'form', 
            'res_id': self.id,
            'target': 'new'
        }