# models/payment_export_wizard.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
from datetime import datetime

class PaymentExportWizard(models.TransientModel):
    _name = 'payment.export.wizard'
    _description = 'Wizard para exportar pagos a archivo TXT'

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

    file_data = fields.Binary(string='Archivo', readonly=True)
    file_name = fields.Char(string='Nombre del archivo', readonly=True)
    state = fields.Selection([
        ('step1', 'Configuración'),
        ('step2', 'Archivo generado')
    ], default='step1')

    total_records = fields.Integer(string='Total de registros', readonly=True)
    
    def action_generate_file(self):
        """Genera el archivo TXT con los datos de los payment_account"""
        
        # Buscar registros del mes y año seleccionados con afiliados activos
        payment_accounts = self.env['affiliate.payment_account'].search([
            ('date_month', '=', self.date_month),
            ('date_year', '=', self.date_year),
            ('affiliate_id.affiliate_type_id.name', '=', 'Activo'),
        ])
        
        if not payment_accounts:
            raise UserError(f'No se encontraron registros para {self.date_month}/{self.date_year} con afiliados activos.')
        
        # Generar contenido del archivo
        file_content = ""
        processed_records = 0
        
        # Crear fecha en formato YYYYMMDD (día 25 del mes seleccionado)
        date_str = f"{self.date_year}{self.date_month}25"
        
        for payment in payment_accounts:
            # Verificar que el afiliado tenga id_benefit
            if not payment.affiliate_id.id_benefit:
                continue
                
            # Calcular: Total Servicios - Pagos
            amount = payment.total_services - payment.payments
            
            # Formatear el monto (usar coma como separador decimal si tiene decimales)
            if amount == int(amount):
                amount_str = str(int(amount))
            else:
                amount_str = f"{amount:.2f}".replace('.', ',')
            
            # Crear línea: ID_BENEFIT    7281  AMOUNT    DATE
            # Usar espacios como separadores según el formato del ejemplo
            line = f"{payment.affiliate_id.id_benefit}    7281  {amount_str}                                             {date_str}\n"
            file_content += line
            processed_records += 1
        
        if processed_records == 0:
            raise UserError('No se encontraron afiliados activos con ID/BENEFIT válido para el período seleccionado.')
        
        # Codificar contenido
        file_data = base64.b64encode(file_content.encode('utf-8'))
        
        # Generar nombre de archivo
        month_names = {
            '01': 'enero', '02': 'febrero', '03': 'marzo', '04': 'abril',
            '05': 'mayo', '06': 'junio', '07': 'julio', '08': 'agosto', 
            '09': 'septiembre', '10': 'octubre', '11': 'noviembre', '12': 'diciembre'
        }
        month_name = month_names.get(self.date_month, self.date_month)
        file_name = f"pagos_{month_name}_{self.date_year}.txt"
        
        # Actualizar wizard
        self.write({
            'file_data': file_data,
            'file_name': file_name,
            'state': 'step2',
            'total_records': processed_records
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.export.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }
    
    def action_download_file(self):
        """Permite descargar el archivo generado"""
        if not self.file_data:
            raise UserError('No hay archivo para descargar.')
            
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=file_data&download=true&filename={self.file_name}',
            'target': 'self',
        }
    
    def action_back(self):
        """Volver al paso anterior"""
        self.write({
            'state': 'step1',
            'file_data': False,
            'file_name': False,
            'total_records': 0
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payment.export.wizard',
            'view_mode': 'form', 
            'res_id': self.id,
            'target': 'new'
        }