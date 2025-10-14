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

    # Archivos individuales - ACTIVOS
    file_data_payments = fields.Binary(string='Archivo Pagos', readonly=True)
    file_name_payments = fields.Char(string='Nombre archivo pagos', readonly=True)
    
    file_data_affiliations = fields.Binary(string='Archivo Altas/Bajas', readonly=True)
    file_name_affiliations = fields.Char(string='Nombre archivo altas/bajas', readonly=True)
    
    file_data_union_fees = fields.Binary(string='Archivo Cuotas', readonly=True)
    file_name_union_fees = fields.Char(string='Nombre archivo cuotas', readonly=True)
    
    # Archivos para JUBILADOS
    file_data_payments_retirees = fields.Binary(string='Archivo Pagos Jubilados', readonly=True)
    file_name_payments_retirees = fields.Char(string='Nombre archivo pagos jubilados', readonly=True)
    
    file_data_union_fees_retirees = fields.Binary(string='Archivo Cuotas Jubilados', readonly=True)
    file_name_union_fees_retirees = fields.Char(string='Nombre archivo cuotas jubilados', readonly=True)
    
    state = fields.Selection([
        ('step1', 'Configuración'),
        ('step2', 'Archivos generados')
    ], default='step1')

    total_records_payments = fields.Integer(string='Registros de pagos', readonly=True)
    total_records_affiliations = fields.Integer(string='Registros de altas/bajas', readonly=True)
    total_records_union_fees = fields.Integer(string='Registros de cuotas sindicales', readonly=True)
    total_records_payments_retirees = fields.Integer(string='Registros de pagos jubilados', readonly=True)
    total_records_union_fees_retirees = fields.Integer(string='Registros de cuotas jubilados', readonly=True)
    
    def _get_date_range(self):
        """Obtiene el rango de fechas del mes/año seleccionado"""
        year = int(self.date_year)
        month = int(self.date_month)
        
        start_date = date(year, month, 1)
        
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        return start_date, end_date
    
    def _format_day_without_leading_zero(self, date_field):
        """Formatea el día removiendo el 0 inicial si existe"""
        day = date_field.strftime('%d')
        return str(int(day))
    
    def _generate_payments_file(self, affiliate_type='Activo', concept_code='7281'):
        """Genera el archivo de pagos (7281 para activos, otro código para jubilados)"""
        payment_accounts = self.env['affiliate.payment_account'].search([
            ('date_month', '=', self.date_month),
            ('date_year', '=', self.date_year),
            ('affiliate_id.affiliate_type_id.name', '=', affiliate_type),
        ])
        
        file_content = ""
        processed_records = 0
        
        date_str = f"{self.date_year}{self.date_month}25"
        
        for payment in payment_accounts:
            if not payment.affiliate_id.id_benefit:
                continue
                
            amount = payment.total_services - payment.payments
            
            if amount == int(amount):
                amount_str = str(int(amount))
            else:
                amount_str = f"{amount:.2f}".replace('.', ',')
            
            line = f"{payment.affiliate_id.id_benefit}    {concept_code}  {amount_str}                                             {date_str}\n"
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"{concept_code}{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def _format_fixed_width_line(self, pe, id_benefit, day, concept, value, action, last_name, first_name, imputation_date):
        """Formatea una línea con anchos fijos"""
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
        
        text = str(text).upper()
        text = unicodedata.normalize('NFD', text)
        
        cleaned_chars = []
        for char in text:
            if unicodedata.category(char) != 'Mn':
                cleaned_chars.append(char)
        
        text = ''.join(cleaned_chars)
        
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
        
        imputation_date = f"{self.date_year}{self.date_month}25"
        
        affiliations = self.env['affiliation.affiliate'].search([
            ('affiliation_date', '>=', start_date),
            ('affiliation_date', '<=', end_date),
            ('id_benefit', '!=', False),
            ('affiliate_type_id.name', '=', 'Activo'),
        ])
        
        for affiliate in affiliations:
            if not affiliate.id_benefit:
                continue
                
            day = self._format_day_without_leading_zero(affiliate.affiliation_date)
            
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, '8522', '', '00',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        disaffiliations = self.env['affiliation.affiliate'].search([
            ('disaffiliation_date', '>=', start_date),
            ('disaffiliation_date', '<=', end_date),
            ('id_benefit', '!=', False),
        ])
        
        for affiliate in disaffiliations:
            if not affiliate.id_benefit:
                continue
                
            day = self._format_day_without_leading_zero(affiliate.disaffiliation_date)
            
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, '8522', '', '99',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"8522{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def _generate_union_fees_file(self, affiliate_type='Activo', concept_code='828'):
        """Genera el archivo de cuotas sindicales (828 para activos, otro código para jubilados)"""
        payment_accounts = self.env['affiliate.payment_account'].search([
            ('date_month', '=', self.date_month),
            ('date_year', '=', self.date_year),
            ('affiliate_id.affiliate_type_id.name', '=', affiliate_type),
        ])
        
        file_content = ""
        processed_records = 0
        
        imputation_date = f"{self.date_year}{self.date_month}25"
        
        for payment in payment_accounts:
            affiliate = payment.affiliate_id
            if not affiliate.id_benefit or not affiliate.affiliation_date:
                continue
            
            day = self._format_day_without_leading_zero(affiliate.affiliation_date)
            
            union_fee = payment.union_fee or 0
            if union_fee == int(union_fee):
                fee_str = str(int(union_fee))
            else:
                fee_str = f"{union_fee:.2f}".replace('.', ',')
            
            line = self._format_fixed_width_line(
                'PE', affiliate.id_benefit, day, concept_code, fee_str, '00',
                affiliate.first_name, affiliate.last_name, imputation_date
            )
            file_content += line
            processed_records += 1
        
        year_short = self.date_year[-2:]
        file_name = f"{concept_code}{self.date_month}{year_short}.txt"
        
        return file_content, file_name, processed_records
    
    def action_generate_payments(self):
        """Genera solo el archivo de pagos (activos)"""
        payments_content, payments_name, payments_count = self._generate_payments_file()
        
        if payments_count == 0:
            raise UserError(f'No se encontraron registros de pagos para el período {self.date_month}/{self.date_year}.')
        
        payments_data = base64.b64encode(payments_content.encode('utf-8'))
        
        self.write({
            'file_data_payments': payments_data,
            'file_name_payments': payments_name,
            'state': 'step2',
            'total_records_payments': payments_count,
        })
        
        return self._return_to_wizard()
    
    def action_generate_payments_retirees(self):
        """Genera solo el archivo de pagos (jubilados)"""
        # NOTA: Ajusta el código de concepto según tus necesidades (por defecto uso 7281)
        payments_content, payments_name, payments_count = self._generate_payments_file(
            affiliate_type='Jubilado', 
            concept_code='7281'  # Cambia esto si necesitas otro código
        )
        
        if payments_count == 0:
            raise UserError(f'No se encontraron registros de pagos de jubilados para el período {self.date_month}/{self.date_year}.')
        
        payments_data = base64.b64encode(payments_content.encode('utf-8'))
        
        self.write({
            'file_data_payments_retirees': payments_data,
            'file_name_payments_retirees': payments_name,
            'state': 'step2',
            'total_records_payments_retirees': payments_count,
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
            'total_records_affiliations': affiliations_count,
        })
        
        return self._return_to_wizard()
    
    def action_generate_union_fees(self):
        """Genera solo el archivo de cuotas sindicales (activos)"""
        union_fees_content, union_fees_name, union_fees_count = self._generate_union_fees_file()
        
        if union_fees_count == 0:
            raise UserError(f'No se encontraron registros de cuotas sindicales para el período {self.date_month}/{self.date_year}.')
        
        union_fees_data = base64.b64encode(union_fees_content.encode('utf-8'))
        
        self.write({
            'file_data_union_fees': union_fees_data,
            'file_name_union_fees': union_fees_name,
            'state': 'step2',
            'total_records_union_fees': union_fees_count,
        })
        
        return self._return_to_wizard()
    
    def action_generate_union_fees_retirees(self):
        """Genera solo el archivo de cuotas sindicales (jubilados)"""
        # NOTA: Ajusta el código de concepto según tus necesidades (por defecto uso 828)
        union_fees_content, union_fees_name, union_fees_count = self._generate_union_fees_file(
            affiliate_type='Jubilado',
            concept_code='828'  # Cambia esto si necesitas otro código
        )
        
        if union_fees_count == 0:
            raise UserError(f'No se encontraron registros de cuotas sindicales de jubilados para el período {self.date_month}/{self.date_year}.')
        
        union_fees_data = base64.b64encode(union_fees_content.encode('utf-8'))
        
        self.write({
            'file_data_union_fees_retirees': union_fees_data,
            'file_name_union_fees_retirees': union_fees_name,
            'state': 'step2',
            'total_records_union_fees_retirees': union_fees_count,
        })
        
        return self._return_to_wizard()
    
    def action_generate_all(self):
        """Genera todos los archivos (activos y jubilados)"""
        # Generar archivos de activos
        payments_content, payments_name, payments_count = self._generate_payments_file()
        affiliations_content, affiliations_name, affiliations_count = self._generate_affiliations_file()
        union_fees_content, union_fees_name, union_fees_count = self._generate_union_fees_file()
        
        # Generar archivos de jubilados
        payments_ret_content, payments_ret_name, payments_ret_count = self._generate_payments_file(
            affiliate_type='Jubilado', concept_code='7281'
        )
        union_fees_ret_content, union_fees_ret_name, union_fees_ret_count = self._generate_union_fees_file(
            affiliate_type='Jubilado', concept_code='828'
        )
        
        # Verificar que al menos un archivo tenga contenido
        total_records = (payments_count + affiliations_count + union_fees_count + 
                        payments_ret_count + union_fees_ret_count)
        
        if total_records == 0:
            raise UserError(f'No se encontraron registros para generar archivos del período {self.date_month}/{self.date_year}.')
        
        # Codificar archivos
        payments_data = base64.b64encode(payments_content.encode('utf-8')) if payments_count > 0 else False
        affiliations_data = base64.b64encode(affiliations_content.encode('utf-8')) if affiliations_count > 0 else False
        union_fees_data = base64.b64encode(union_fees_content.encode('utf-8')) if union_fees_count > 0 else False
        payments_ret_data = base64.b64encode(payments_ret_content.encode('utf-8')) if payments_ret_count > 0 else False
        union_fees_ret_data = base64.b64encode(union_fees_ret_content.encode('utf-8')) if union_fees_ret_count > 0 else False
        
        # Actualizar wizard
        self.write({
            'file_data_payments': payments_data,
            'file_name_payments': payments_name if payments_count > 0 else False,
            'file_data_affiliations': affiliations_data,
            'file_name_affiliations': affiliations_name if affiliations_count > 0 else False,
            'file_data_union_fees': union_fees_data,
            'file_name_union_fees': union_fees_name if union_fees_count > 0 else False,
            'file_data_payments_retirees': payments_ret_data,
            'file_name_payments_retirees': payments_ret_name if payments_ret_count > 0 else False,
            'file_data_union_fees_retirees': union_fees_ret_data,
            'file_name_union_fees_retirees': union_fees_ret_name if union_fees_ret_count > 0 else False,
            'state': 'step2',
            'total_records_payments': payments_count,
            'total_records_affiliations': affiliations_count,
            'total_records_union_fees': union_fees_count,
            'total_records_payments_retirees': payments_ret_count,
            'total_records_union_fees_retirees': union_fees_ret_count,
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
    
    def action_download_payments_retirees(self):
        """Descarga el archivo de pagos (jubilados)"""
        if not self.file_data_payments_retirees:
            raise UserError('No hay archivo de pagos de jubilados para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data_payments_retirees&download=true&filename={self.file_name_payments_retirees}',
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
    
    def action_download_union_fees_retirees(self):
        """Descarga el archivo de cuotas sindicales (jubilados)"""
        if not self.file_data_union_fees_retirees:
            raise UserError('No hay archivo de cuotas sindicales de jubilados para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data_union_fees_retirees&download=true&filename={self.file_name_union_fees_retirees}',
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
            'file_data_payments_retirees': False,
            'file_name_payments_retirees': False,
            'file_data_union_fees_retirees': False,
            'file_name_union_fees_retirees': False,
            'total_records_payments': 0,
            'total_records_affiliations': 0,
            'total_records_union_fees': 0,
            'total_records_payments_retirees': 0,
            'total_records_union_fees_retirees': 0,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.export.wizard',
            'view_mode': 'form', 
            'res_id': self.id,
            'target': 'new'
        }