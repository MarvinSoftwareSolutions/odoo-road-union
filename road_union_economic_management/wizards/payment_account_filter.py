from odoo import models, fields, api
from datetime import datetime

class PaymentAccountFilterWizard(models.TransientModel):
    _name = 'payment.account.filter.wizard'
    _description = 'Wizard para filtrar cuentas de pago por mes y año'

    # Campo para almacenar las opciones disponibles
    available_periods = fields.Text(compute='_compute_available_periods', store=False)
    
    @api.depends_context('force_refresh')
    def _compute_available_periods(self):
        """Computa las combinaciones mes-año disponibles"""
        for wizard in self:
            wizard.available_periods = str(wizard._get_month_year_selection())

    @api.model
    def _get_month_year_selection(self):
        """Obtiene las combinaciones mes-año que tienen registros"""
        # Forzar búsqueda fresca cada vez
        records = self.env['affiliate.payment_account'].search([])
        combinations = set()
        
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        
        for record in records:
            if record.date_month and record.date_year:
                key = f"{record.date_month}-{record.date_year}"
                month_name = month_names.get(record.date_month, record.date_month)
                label = f"{month_name} {record.date_year}"
                combinations.add((key, label))
        
        # Ordenar por año y mes (más reciente primero)
        sorted_combinations = sorted(combinations, key=lambda x: (x[0].split('-')[1], x[0].split('-')[0]), reverse=True)
        
        return sorted_combinations

    month_year = fields.Selection(
        selection=lambda self: self._get_month_year_selection(),
        string='Período',
        required=True,
    )

    @api.model
    def _get_current_month_year(self):
        """Obtiene el período actual en formato MM-YYYY"""
        current_month = datetime.now().strftime('%m')
        current_year = str(datetime.now().year)
        return f"{current_month}-{current_year}"

    @api.model
    def default_get(self, fields_list):
        """Establece el valor por defecto al período actual si existe"""
        res = super().default_get(fields_list)
        
        if 'month_year' in fields_list:
            current_period = self._get_current_month_year()
            available_periods = [item[0] for item in self._get_month_year_selection()]
            
            if current_period in available_periods:
                res['month_year'] = current_period
            elif available_periods:
                res['month_year'] = available_periods[0]  # El más reciente
                
        return res

    # Campos computados para mostrar estadísticas
    total_records = fields.Integer(
        string="Total de Registros",
        compute='_compute_statistics'
    )
    
    total_confirmed = fields.Integer(
        string="Confirmados",
        compute='_compute_statistics'
    )
    
    total_draft = fields.Integer(
        string="Borradores",
        compute='_compute_statistics'
    )
    
    total_final_balance = fields.Float(
        string="Balance Final Total",
        compute='_compute_statistics'
    )

    @api.depends('month_year')
    def _compute_statistics(self):
        for wizard in self:
            if wizard.month_year:
                month, year = wizard.month_year.split('-')
                records = self.env['affiliate.payment_account'].search([
                    ('date_month', '=', month),
                    ('date_year', '=', year)
                ])
                
                wizard.total_records = len(records)
                wizard.total_confirmed = len(records.filtered(lambda r: r.state == 'confirmed'))
                wizard.total_draft = len(records.filtered(lambda r: r.state == 'draft'))
                wizard.total_final_balance = sum(records.mapped('final_balance'))
            else:
                wizard.total_records = 0
                wizard.total_confirmed = 0
                wizard.total_draft = 0
                wizard.total_final_balance = 0.0

    def action_show_payment_accounts(self):
        """Muestra los payment accounts filtrados por mes y año"""
        self.ensure_one()
        
        if not self.month_year:
            return
            
        month, year = self.month_year.split('-')
        
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        
        month_name = month_names.get(month, month)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Resúmenes Económicos - {month_name} {year}',
            'res_model': 'affiliate.payment_account',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('road_union_economic_management.view_payment_account_tree_grouped').id, 'tree'),
                (False, 'form'),
            ],
            'domain': [
                ('date_month', '=', month),
                ('date_year', '=', year)
            ],
            'context': {
                'default_date_month': month,
                'default_date_year': year,
            },
            'target': 'current',
        }

    def action_show_confirmed_only(self):
        """Muestra solo los registros confirmados"""
        self.ensure_one()
        
        if not self.month_year:
            return
            
        month, year = self.month_year.split('-')
        
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        
        month_name = month_names.get(month, month)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Confirmados - {month_name} {year}',
            'res_model': 'affiliate.payment_account',
            'view_mode': 'tree,form',
            'domain': [
                ('date_month', '=', month),
                ('date_year', '=', year),
                ('state', '=', 'confirmed')
            ],
            'context': {
                'default_date_month': month,
                'default_date_year': year,
                'default_state': 'confirmed',
            },
            'target': 'current',
        }

    def action_show_draft_only(self):
        """Muestra solo los registros en borrador"""
        self.ensure_one()
        
        if not self.month_year:
            return
            
        month, year = self.month_year.split('-')
        
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        
        month_name = month_names.get(month, month)
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Borradores - {month_name} {year}',
            'res_model': 'affiliate.payment_account',
            'view_mode': 'tree,form',
            'domain': [
                ('date_month', '=', month),
                ('date_year', '=', year),
                ('state', '=', 'draft')
            ],
            'context': {
                'default_date_month': month,
                'default_date_year': year,
                'default_state': 'draft',
            },
            'target': 'current',
        }
    def action_refresh_periods(self):
        """Refresca las opciones disponibles"""
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }