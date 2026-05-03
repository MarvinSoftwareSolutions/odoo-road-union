from odoo import models, fields, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class AffiliateClassBasicHistory(models.Model):
    _name = "affiliate.class.basic.history"
    _description = "Monthly History of Basic Amounts by Class"
    _order = "date_year desc, date_month desc, class_number asc"

    def _default_class_basic_id(self):
        return self.env['affiliate.class.basic'].search(
            [('class_number', '=', 1)], limit=1).id

    class_basic_id = fields.Many2one(
        comodel_name="affiliate.class.basic",
        string="Clase",
        required=True,
        ondelete="cascade",
        default=_default_class_basic_id,
    )

    class_number = fields.Integer(
        string="N° Clase",
        related="class_basic_id.class_number",
        store=True,
    )

    date_month = fields.Selection(
        selection=[
            ('01', 'Enero'), ('02', 'Febrero'), ('03', 'Marzo'),
            ('04', 'Abril'), ('05', 'Mayo'), ('06', 'Junio'),
            ('07', 'Julio'), ('08', 'Agosto'), ('09', 'Septiembre'),
            ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre'),
        ],
        string="Mes",
        required=True,
    )

    @api.model
    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(year), str(year)) for year in
                reversed(range(current_year - 10, current_year + 11))]

    date_year = fields.Selection(
        selection=_get_year_selection,
        string="Año",
        required=True,
    )

    basic_amount = fields.Float(
        string="Básico",
        digits='Product Price',
        required=True,
    )

    manually_modified = fields.Boolean(
        string="Modificado manualmente",
        default=False,
    )

    _sql_constraints = [
        ('unique_class_month_year',
         'unique(class_basic_id, date_month, date_year)',
         'Ya existe un registro de historial para esta clase, mes y año.')
    ]

    @api.model
    def load(self, fields, data):
        """Override para hacer upsert por la clave natural
        ``(class_basic_id, date_month, date_year)``.

        Si una fila importada matchea un registro existente por la clave
        natural, se inyecta el External ID del existente para que Odoo
        actualice (en vez de fallar contra el constraint UNIQUE).
        Las filas se reportan como warnings en el preview de "Probar".
        """
        natural_key = ['class_basic_id', 'date_month', 'date_year']
        if not all(k in fields for k in natural_key) or 'id' in fields:
            return super().load(fields, data)

        idx = {k: fields.index(k) for k in natural_key}
        IMD = self.env['ir.model.data']
        ClassBasic = self.env['affiliate.class.basic']
        # Cambiamos `class_basic_id` por `class_basic_id/.id` para que Odoo
        # resuelva el Many2one por database id en vez de hacer name_search
        # con ilike (ambiguo: "Clase 1" matchea con Clase 1, 10, 11, ..., 19)
        new_fields = ['id'] + list(fields)
        new_fields[1 + idx['class_basic_id']] = 'class_basic_id/.id'
        new_data = []
        warnings_msgs = []

        # Mapeo label → value para los campos Selection (date_month, date_year)
        # ya que el archivo trae "Abril" pero la DB almacena "04"
        month_label_to_value = {
            label: value
            for value, label in self._fields['date_month'].selection
        }
        year_label_to_value = {
            label: value
            for value, label in self._fields['date_year'].selection(self)
        }

        for row_idx, row in enumerate(data, start=2):
            class_basic_val = row[idx['class_basic_id']]
            date_month_raw = row[idx['date_month']]
            date_year_raw = row[idx['date_year']]

            if class_basic_val in (None, '', False) or not date_month_raw or not date_year_raw:
                new_data.append(['', *row])
                continue

            # Normalizar: el archivo puede traer "Abril" (label) o "04" (value)
            date_month = month_label_to_value.get(date_month_raw, date_month_raw)
            date_year = year_label_to_value.get(date_year_raw, date_year_raw)

            # Resolver el class_basic_id. Estrategia:
            # 1) entero pequeño (1-20) → buscar por class_number (el caso típico)
            # 2) string con punto → external id (module.name)
            # 3) entero grande → id de la base
            # 4) string libre → display_name
            class_basic = ClassBasic.browse()
            try:
                as_int = int(class_basic_val)
                if 1 <= as_int <= 20:
                    class_basic = ClassBasic.search(
                        [('class_number', '=', as_int)], limit=1)
                elif not class_basic:
                    class_basic = ClassBasic.browse(as_int)
                    if not class_basic.exists():
                        class_basic = ClassBasic.browse()
            except (TypeError, ValueError):
                pass
            if not class_basic and isinstance(class_basic_val, str):
                if '.' in class_basic_val:
                    class_basic = self.env.ref(
                        class_basic_val, raise_if_not_found=False) or ClassBasic.browse()
                if not class_basic:
                    class_basic = ClassBasic.search(
                        [('display_name', '=', class_basic_val)], limit=1)

            if not class_basic:
                # No pudimos resolver la clase - reportar como error y skip
                warnings_msgs.append({
                    'type': 'error',
                    'message': _("Fila %(row)s: no se pudo resolver la clase '%(val)s'") % {
                        'row': row_idx,
                        'val': class_basic_val,
                    },
                    'rows': {'from': row_idx - 1, 'to': row_idx - 1},
                })
                continue

            # Reemplazar el valor de class_basic_id por su database id (string)
            # ya que cambiamos el field name a `class_basic_id/.id`
            modified_row = list(row)
            modified_row[idx['class_basic_id']] = str(class_basic.id)

            existing = self.search([
                ('class_basic_id', '=', class_basic.id),
                ('date_month', '=', date_month),
                ('date_year', '=', date_year),
            ], limit=1)

            if not existing:
                new_data.append(['', *modified_row])
                continue

            imd = IMD.search([
                ('model', '=', self._name),
                ('res_id', '=', existing.id),
            ], limit=1)
            if imd:
                xml_id = f"{imd.module}.{imd.name}"
            else:
                ext_name = f'class_basic_history_{existing.id}'
                IMD.create({
                    'module': '__import__',
                    'name': ext_name,
                    'model': self._name,
                    'res_id': existing.id,
                })
                xml_id = f"__import__.{ext_name}"

            new_data.append([xml_id, *modified_row])
            warnings_msgs.append({
                'type': 'warning',
                'message': _('Fila %(row)s: ya existe historial para Clase %(cls)s %(month)s/%(year)s — se actualizará.') % {
                    'row': row_idx,
                    'cls': class_basic.class_number,
                    'month': date_month,
                    'year': date_year,
                },
                'rows': {'from': row_idx - 1, 'to': row_idx - 1},
            })

        result = super().load(new_fields, new_data)
        if warnings_msgs:
            result.setdefault('messages', []).extend(warnings_msgs)
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create: cuando se crea un registro de clase 1 desde la vista,
        marca manually_modified=True y propaga a todas las clases.
        """
        records = super().create(vals_list)

        if not self.env.context.get('_skip_history_propagation'):
            for record in records:
                if record.class_number == 1:
                    self.set_class1_basic_for_month(
                        record.date_month, record.date_year, record.basic_amount)

        return records

    def name_get(self):
        month_names = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre',
        }
        result = []
        for record in self:
            month = month_names.get(record.date_month, record.date_month)
            name = f"Clase {record.class_number} - {month} {record.date_year} - ${record.basic_amount:,.2f}"
            result.append((record.id, name))
        return result

    @api.model
    def get_basic_for_month(self, class_number, month, year):
        """
        Obtiene el básico de una clase para un mes/año dado.
        Busca registro exacto -> si no existe, camina hacia atrás -> fallback al básico actual.
        """
        month = str(month).zfill(2)
        year = str(year)

        # Buscar registro exacto
        record = self.search([
            ('class_number', '=', class_number),
            ('date_month', '=', month),
            ('date_year', '=', year),
        ], limit=1)
        if record:
            return record.basic_amount

        # Caminar hacia atrás: buscar el registro más reciente anterior
        all_records = self.search([
            ('class_number', '=', class_number),
        ], order='date_year desc, date_month desc')

        target_date = int(year) * 100 + int(month)
        for rec in all_records:
            rec_date = int(rec.date_year) * 100 + int(rec.date_month)
            if rec_date < target_date:
                return rec.basic_amount

        # Fallback: básico actual del modelo affiliate.class.basic
        class_basic = self.env['affiliate.class.basic'].search([
            ('class_number', '=', class_number),
            ('active', '=', True),
        ], limit=1)
        return class_basic.basic_amount if class_basic else 0.0

    @api.model
    def set_class1_basic_for_month(self, month, year, amount):
        """
        Punto de entrada para ediciones del básico de clase 1.
        - Upsert clase 1 con manually_modified=True
        - Upsert clases 2-20 con amount * class_index, manually_modified=False
        - Propagar mes a mes hacia adelante hasta encontrar otro manually_modified=True en clase 1
        - Recalcular union_fee en payment_accounts de meses afectados
        """
        month = str(month).zfill(2)
        year = str(year)

        ClassBasic = self.env['affiliate.class.basic']
        all_classes = ClassBasic.search([], order='class_number asc')

        # Upsert para el mes dado
        affected_months = []
        self._upsert_all_classes(month, year, amount, all_classes, manually_modified_class1=True)
        affected_months.append((month, year))

        # Propagar hacia adelante
        next_month, next_year = self._next_month(month, year)
        while True:
            # Verificar si existe un registro de clase 1 marcado como manually_modified
            class1_basic = ClassBasic.search([('class_number', '=', 1)], limit=1)
            if not class1_basic:
                break

            next_record = self.search([
                ('class_basic_id', '=', class1_basic.id),
                ('date_month', '=', next_month),
                ('date_year', '=', next_year),
            ], limit=1)

            if next_record and next_record.manually_modified:
                # Encontramos un mes con modificación manual, detenemos propagación
                break

            if not next_record:
                # No hay más registros hacia adelante, detenemos
                break

            # Propagar: actualizar este mes con el mismo amount de clase 1
            self._upsert_all_classes(next_month, next_year, amount, all_classes, manually_modified_class1=False)
            affected_months.append((next_month, next_year))

            next_month, next_year = self._next_month(next_month, next_year)

        # Recalcular union_fee en payment_accounts de meses afectados
        self._recompute_union_fees_for_months(affected_months)

        # Actualizar affiliate.class.basic si el registro más reciente cambió
        latest_class1 = self.search([
            ('class_number', '=', 1),
        ], order='date_year desc, date_month desc', limit=1)

        if latest_class1:
            class1_basic = ClassBasic.search([('class_number', '=', 1)], limit=1)
            if class1_basic and class1_basic.basic_amount != latest_class1.basic_amount:
                class1_basic.with_context(
                    _skip_history_creation=True
                ).write({
                    'basic_amount': latest_class1.basic_amount,
                    'basic_amount_class1': latest_class1.basic_amount,
                })

    @api.model
    def _upsert_all_classes(self, month, year, class1_amount, all_classes, manually_modified_class1=False):
        """Crea o actualiza registros de historial para todas las clases en un mes/año."""
        for class_basic in all_classes:
            if class_basic.class_number == 1:
                amount = class1_amount
                manually = manually_modified_class1
            else:
                amount = class1_amount * class_basic.class_index
                manually = False

            existing = self.search([
                ('class_basic_id', '=', class_basic.id),
                ('date_month', '=', month),
                ('date_year', '=', year),
            ], limit=1)

            if existing:
                vals = {'basic_amount': amount}
                if class_basic.class_number == 1:
                    vals['manually_modified'] = manually
                # Bypass write override to avoid recursion
                super(AffiliateClassBasicHistory, existing).write(vals)
            else:
                self.with_context(_skip_history_propagation=True).create({
                    'class_basic_id': class_basic.id,
                    'date_month': month,
                    'date_year': year,
                    'basic_amount': amount,
                    'manually_modified': manually,
                })

    @api.model
    def _next_month(self, month, year):
        """Retorna el mes y año siguiente."""
        m = int(month)
        y = int(year)
        if m == 12:
            return '01', str(y + 1)
        return str(m + 1).zfill(2), str(y)

    @api.model
    def _recompute_union_fees_for_months(self, months):
        """Recalcula union_fee para todos los payment_account de los meses dados."""
        PaymentAccount = self.env['affiliate.payment_account']
        for month, year in months:
            records = PaymentAccount.search([
                ('date_month', '=', month),
                ('date_year', '=', year),
            ])
            for record in records:
                record._compute_union_fee()
                record._compute_total()
                record._compute_final_balance()
                record._update_subsequent_months_initial_balance()

    @api.model
    def ensure_month_exists(self, month, year):
        """
        Asegura que existan registros de historial para todas las clases en un mes/año.
        Si no existen, los crea heredando del mes anterior.
        """
        month = str(month).zfill(2)
        year = str(year)

        ClassBasic = self.env['affiliate.class.basic']
        all_classes = ClassBasic.search([], order='class_number asc')

        for class_basic in all_classes:
            existing = self.search([
                ('class_basic_id', '=', class_basic.id),
                ('date_month', '=', month),
                ('date_year', '=', year),
            ], limit=1)

            if not existing:
                # Heredar del mes anterior
                amount = self.get_basic_for_month(class_basic.class_number, month, year)
                self.with_context(_skip_history_propagation=True).create({
                    'class_basic_id': class_basic.id,
                    'date_month': month,
                    'date_year': year,
                    'basic_amount': amount,
                    'manually_modified': False,
                })

    def unlink(self):
        """
        Override unlink: al borrar registros de historial de clase 1,
        también borra los registros de las demás clases del mismo mes/año.
        Actualiza affiliate.class.basic con el valor del registro más reciente restante.
        Recalcula union_fee para los meses afectados.
        """
        if self.env.context.get('_skip_cascade_delete'):
            return super().unlink()

        # Capturar meses afectados y meses con clase 1
        affected_months = set()
        class1_months = set()
        for record in self:
            affected_months.add((record.date_month, record.date_year))
            if record.class_number == 1:
                class1_months.add((record.date_month, record.date_year))

        result = super().unlink()

        if class1_months:
            # Borrar registros de otras clases para los mismos meses
            for month, year in class1_months:
                other_records = self.search([
                    ('date_month', '=', month),
                    ('date_year', '=', year),
                ])
                if other_records:
                    other_records.with_context(_skip_cascade_delete=True).unlink()

            # Actualizar affiliate.class.basic desde el registro más reciente restante
            ClassBasic = self.env['affiliate.class.basic']
            class1_basic = ClassBasic.search([('class_number', '=', 1)], limit=1)

            if class1_basic:
                latest_class1 = self.search([
                    ('class_number', '=', 1),
                ], order='date_year desc, date_month desc', limit=1)

                if latest_class1:
                    # Propagar el valor del registro más reciente restante
                    # Usar _skip_history_creation para no re-crear registros
                    class1_basic.with_context(
                        _skip_history_creation=True
                    ).write({
                        'basic_amount': latest_class1.basic_amount,
                        'basic_amount_class1': latest_class1.basic_amount,
                    })

        # Recalcular union_fee de meses afectados
        if affected_months:
            self._recompute_union_fees_for_months(list(affected_months))

        return result

    def write(self, vals):
        """
        Override write: cuando se edita basic_amount de clase 1 desde la vista,
        marca manually_modified=True y propaga via set_class1_basic_for_month.
        """
        # Detectar si se edita basic_amount en un registro de clase 1
        if 'basic_amount' in vals:
            for record in self:
                if record.class_number == 1:
                    # Llamar set_class1_basic_for_month que maneja todo
                    self.env['affiliate.class.basic.history'].set_class1_basic_for_month(
                        record.date_month, record.date_year, vals['basic_amount']
                    )
                    return True

        return super().write(vals)
