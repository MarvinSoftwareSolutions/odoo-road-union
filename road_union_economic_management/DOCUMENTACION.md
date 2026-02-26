# road_union_economic_management - Documentacion

**Nombre en Odoo:** Sindicato vialidad - Gestion economica de afiliados
**Autor:** FMP solutions S.A.S. / Marvin Software Solutions
**Version:** 1.0
**Licencia:** AGPL-3
**Dependencias:** `base`, `base_automation`, `union_affiliation`, `road_union_affiliation`
**Branch principal:** `16.0`
**Repositorio:** MarvinSoftwareSolutions/odoo-road-union

---

## Proposito

Sistema integral de **gestion economica** del sindicato de vialidad. Maneja cuentas corrientes mensuales por afiliado, gastos de farmacia con descuentos acumulados, clases salariales basicas, liquidaciones a proveedores, y exportacion de archivos para el sistema META4 (integracion con el sistema bancario/previsional del Estado).

---

## Modelos

### 1. `affiliation.affiliate` (extension)

**Archivo:** `models/affiliate.py`

Extiende el afiliado con campos economicos.

| Campo | Tipo | Descripcion |
|---|---|---|
| `payment_account_ids` | One2many → `affiliate.payment_account` | Cuentas corrientes mensuales |
| `id_benefit` | Char (required, unique) | Identificador ID/BENEFIT para META4 |

**Metodos:**

- **`create(vals)`** — Al crear un afiliado, automaticamente crea:
  1. Un registro de `affiliate.pharmacy.expenses` para el mes actual
  2. Un registro de `affiliate.payment_account` para el mes actual
- **`action_create_current_month_payment()`** — Boton manual para crear la cuenta corriente del mes actual si no existe.

---

### 2. `affiliate.payment_account` (Cuenta Corriente Mensual)

**Archivo:** `models/payment_account.py`

Modelo central de la gestion economica. Cada registro es un **resumen mensual** por afiliado con todos los conceptos de servicios, cuota sindical, pagos y saldo.

**Restriccion unica:** Un solo registro por afiliado + mes + anio.

#### Campos de informacion

| Campo | Tipo | Descripcion |
|---|---|---|
| `affiliate_id` | Many2one (required) | Afiliado |
| `affiliate_type` | Related (stored) | Tipo de relacion laboral |
| `affiliate_name` | Computed (stored) | Nombre del afiliado |
| `affiliate_class` | Related | Clase/categoria |
| `affiliate_number` | Related | UID del afiliado |
| `cuil` | Related | CUIL |
| `id_benefit` | Related | ID/BENEFIT |
| `date_month` | Selection (required) | Mes (01-12) |
| `date_year` | Selection (required) | Anio |
| `state` | Selection | `draft` / `confirmed` |

#### Campos de saldo

| Campo | Tipo | Descripcion |
|---|---|---|
| `has_previous_month` | Boolean (computed) | Indica si existe mes anterior |
| `initial_balance` | Float (computed + inverse) | Saldo inicial. Se calcula del `final_balance` del mes anterior. Es editable manualmente solo si no existe mes anterior |
| `final_balance` | Float (computed) | Saldo final = total - pagos - caja jubilaciones - meta4 |

#### Campos de servicios (todos Float)

| Categoria | Campos |
|---|---|
| Farmacia | `pharmacy_total`, `pharmacy_installment` (cuotas, Char) |
| Optica | `optical_total` |
| Odontologia | `odontology_total`, `odontology_installment` (Char) |
| Alojamientos | `punilla_total`, `solar`, `caruso`, `parque_del_sol`, `salguero`, `tres_provincias` |
| Prestamos | `ecco_loan`, `emi_loan`, `emergency_loan`, `suoem_loan` |
| Turismo | `tourism_total`, `tourism_installment` (Char) |
| Ayuda | `aid_total`, `aid_installment` (Char) |
| Fiesta | `party_total`, `party_installment` (Char) |
| Salon | `hall_total`, `hall_installment` (Char) |
| Otros | `otros_1`, `otros_2` |

#### Campos calculados de resumen

| Campo | Calculo |
|---|---|
| `total_services` | saldo_inicial + suma de todos los servicios y prestamos |
| `union_fee` | Cuota sindical (ver formula abajo) |
| `total` | total_services + union_fee |
| `payments` | Pagos manuales (ingreso manual) |
| `pension_fund` | Caja de Jubilaciones (ingreso manual) |
| `meta4` | Deducciones META4 (ingreso manual) |
| `final_balance` | total - payments - pension_fund - meta4 |

#### Formula de cuota sindical (`union_fee`)

```
Para afiliados activos:
  union_fee = (basico_clase_afiliado * 0.015) + (basico_clase_15 * 0.015)

Para jubilados/pensionados/retirados:
  union_fee = calculo_anterior * 0.75
```

#### Metodos clave

- **`create_monthly_records_for_all_affiliates(month, year)`** — Crea registros para TODOS los afiliados activos del mes/anio indicado. Evita duplicados.
- **`create_record_for_new_affiliate(affiliate_id)`** — Crea registro del mes actual para un afiliado nuevo.
- **`cron_create_monthly_records()`** — Metodo llamado por el CRON el dia 1 de cada mes.
- **`_update_subsequent_months_initial_balance()`** — Cuando se modifica un registro, propaga los cambios de saldo a todos los meses siguientes.
- **`_compute_initial_balance()`** — Trae el `final_balance` del mes anterior, o mantiene el valor manual si es el primer mes.

---

### 3. `affiliate.class.basic` (Clase Salarial Basica)

**Archivo:** `models/payment_account.py`

Tabla de referencia de clases salariales. Todas las clases dependen del basico de **clase 1**.

| Campo | Tipo | Descripcion |
|---|---|---|
| `class_number` | Integer (required, unique) | Numero de clase (1-20) |
| `class_index` | Float (required) | Indice multiplicador relativo a clase 1 |
| `basic_amount` | Float (computed, stored) | Basico = class_index * basico_clase_1 |
| `basic_amount_class1` | Float | Monto basico de referencia (solo en clase 1) |
| `active` | Boolean | Activa |

**Logica:**
- Solo la **clase 1** es editable en su `basic_amount_class1`.
- Todas las demas clases calculan su basico como `class_index * basic_amount de clase 1`.
- Al modificar la clase 1, se recalculan automaticamente todas las demas clases y las cuotas sindicales del mes actual en adelante.

**Datos precargados** (20 clases):

| Clase | Indice | Basico inicial |
|---|---|---|
| 1 | 1.0 | $184.663,95 |
| 2-6 | 1.7 | (calculado) |
| 7 | 1.89 | (calculado) |
| 8 | 2.1 | (calculado) |
| ... | ... | ... |
| 20 | 7.5 | (calculado) |

---

### 4. `affiliate.pharmacy.expenses` (Gastos de Farmacia)

**Archivo:** `models/pharmacies.py`

Seguimiento mensual de gastos de farmacia por afiliado, con **6 farmacias** configuradas.

| Campo | Tipo | Descripcion |
|---|---|---|
| `affiliate_id` | Many2one (required) | Afiliado |
| `month` | Selection (required) | Mes (01-12) |
| `year` | Integer (required) | Anio |

#### Campos por farmacia

Cada farmacia tiene un campo de gasto normal y otro de venta libre (`_vl`):

| Farmacia | Gasto | Venta Libre |
|---|---|---|
| Estrella | `gasto_farmacia1` | `gasto_farmacia1_vl` |
| Nueva Cba | `gasto_farmacia2` | `gasto_farmacia2_vl` |
| General Paz | `gasto_farmacia3` | `gasto_farmacia3_vl` |
| Medicarlo | `gasto_farmacia4` | `gasto_farmacia4_vl` |
| Farmavida | `gasto_farmacia5` | `gasto_farmacia5_vl` |
| Del Indio | `gasto_farmacia6` | `gasto_farmacia6_vl` |

#### Campos calculados

| Campo | Calculo |
|---|---|
| `suma_mes` | Suma de los 6 gastos de farmacia (sin VL) |
| `vta_libre` | Suma de los 6 gastos de venta libre |
| `saldo_acumulado` | saldo_acumulado del mes anterior + suma_mes del mes actual |
| `descuento_realizado` | Formula con tope de $125.000 (ver abajo) |
| `desc_afil` | suma_mes - descuento_realizado + vta_libre |
| `disponible_40` | 125.000 - (suma_mes + saldo_acumulado) |

#### Formula de descuento al 40%

```
Si (suma_mes + saldo_acumulado) < 125.000:
    descuento = suma_mes * 0.40

Si saldo_acumulado > 125.000:
    descuento = 0

Si no:
    descuento = (125.000 - saldo_acumulado) * 0.40
```

El descuento se aplica sobre los gastos de farmacia hasta un tope acumulado anual de $125.000. Una vez superado el tope, el afiliado paga el 100%.

**Propagacion:** Al modificar un gasto, se recalculan automaticamente los `saldo_acumulado` de todos los meses siguientes del mismo afiliado.

---

### 5. `sindicato.proveedor` (Proveedor)

**Archivo:** `models/provider_payments.py`

Proveedores de servicios del sindicato.

| Campo | Tipo | Descripcion |
|---|---|---|
| `nombre` | Char (required) | Nombre del proveedor |
| `tipo` | Selection (required) | `farmacia` / `otro` |
| `porcentaje_comision` | Float (required) | Porcentaje de comision (0-100) |
| `activo` | Boolean | Activo |
| `importe_ids` | One2many | Importes mensuales |

**Restriccion:** `porcentaje_comision` debe estar entre 0 y 100.

**Datos precargados** (6 farmacias con 10% de comision):
Estrella, Nueva Cba, General Paz, Medicarlo, Farmavida, Del Indio.

---

### 6. `sindicato.liquidacion.mensual` (Liquidacion Mensual)

**Archivo:** `models/provider_payments.py`

Resumen mensual de liquidaciones a proveedores.

| Campo | Tipo | Descripcion |
|---|---|---|
| `mes` | Integer (required) | Mes |
| `anio` | Integer (required) | Anio |
| `descripcion` | Char (computed) | "Mes Anio" |
| `importe_ids` | One2many | Detalle por proveedor |
| `total_importe_plan` | Monetary (computed) | Total importe plan |
| `total_comision` | Monetary (computed) | Total comisiones |
| `total_importe_pagar` | Monetary (computed) | Total a pagar (plan - comisiones) |
| `total_farmacias` | Monetary (computed) | Total 40% farmacias |

**Restriccion unica:** Un solo registro por mes + anio.

**Metodos:**
- **`action_generar_lineas()`** — Boton que crea lineas de importe para todos los proveedores activos que no esten ya en la liquidacion.
- **`get_or_create_current_month()`** — Obtiene o crea la liquidacion del mes actual con sus lineas.

---

### 7. `sindicato.importe.mensual` (Importe por Proveedor)

**Archivo:** `models/provider_payments.py`

Detalle de cada proveedor dentro de una liquidacion mensual.

| Campo | Tipo | Descripcion |
|---|---|---|
| `liquidacion_id` | Many2one (required) | Liquidacion |
| `proveedor_id` | Many2one (required) | Proveedor |
| `importe_total_plan` | Monetary | Importe del plan |
| `porcentaje_comision` | Float (related) | Comision % del proveedor |
| `comision` | Monetary (computed) | importe * (% / 100) |
| `importe_a_pagar` | Monetary (computed) | importe - comision |
| `es_farmacia` | Boolean (computed) | Si el proveedor es farmacia |
| `cuarenta_porciento_farmacias` | Monetary | Campo manual para 40% farmacias |

**Restriccion unica:** Un solo registro por proveedor + liquidacion.

---

## Wizards

### 1. Filtro de Cuentas Corrientes (`payment.account.filter.wizard`)

**Archivo:** `wizard/payment_account_filter.py`

Permite filtrar y ver estadisticas de las cuentas corrientes por periodo.

| Campo | Tipo | Descripcion |
|---|---|---|
| `month_year` | Selection (dynamic) | Periodo seleccionado (MM-YYYY) |
| `total_records` | Integer (computed) | Total de registros |
| `total_confirmed` | Integer (computed) | Registros confirmados |
| `total_draft` | Integer (computed) | Registros en borrador |
| `total_final_balance` | Float (computed) | Saldo final total |

**Acciones:**
- Ver todos los registros del periodo
- Ver solo confirmados
- Ver solo borradores
- Refrescar periodos disponibles

---

### 2. Exportacion META4 (`payment.export.wizard`)

**Archivo:** `wizard/meta_4_download.py`

Wizard de **dos pasos** para generar archivos TXT compatibles con el sistema META4.

**Paso 1:** Seleccionar mes y anio.

**Paso 2:** Descargar archivos generados.

#### Archivos que genera

| Archivo | Concepto | Poblacion | Descripcion |
|---|---|---|---|
| Pagos | 7281 | Activos | Deducciones de servicios |
| Altas/Bajas | 8522 | Todos | Afiliaciones y desafiliaciones del mes |
| Cuota Sindical | 828 | Activos | Cuota sindical |
| Pagos Jubilados | 7281 | Jubilados | Deducciones de servicios jubilados |
| Cuota Sindical Jubilados | 828 | Jubilados | Cuota sindical jubilados |

#### Formato de archivos

Archivos de texto con **formato de ancho fijo** (campos posicionales). Cada linea contiene:
- PE (periodo)
- ID/BENEFIT
- Dia
- Codigo de concepto
- Valor
- Accion (alta/baja)
- Apellido y nombre
- Fecha de imputacion

**Tratamiento de texto:** Se convierte a mayusculas, se eliminan tildes/diacriticos pero se conserva la enie (n).

---

## Vistas

### Cuentas Corrientes (`payment_account_current_views.xml`)

- **Vista tree editable** con todos los campos de servicios, prestamos y resumen
- **Vista form** organizada en secciones:
  - Informacion del afiliado (readonly)
  - Saldo inicial (condicional: readonly si existe mes anterior, editable si es el primer mes)
  - Servicios por categoria
  - Prestamos
  - Resumen economico (totales calculados)
- **Vista search** con filtros por borrador/confirmado y agrupaciones por estado, afiliado, clase, mes, anio
- Decoraciones de color segun estado (confirmed=verde)

### Clases Salariales (`affiliate_class_basic_views.xml`)

- **Vista tree editable** con numero de clase, indice, basico y activo
- **Vista form** con seccion especial para clase 1 (unica editable)
- Boton "Recalcular Todos"

### Gastos de Farmacia (`pharmacies_views.xml`)

- **Vista tree** con los 12 campos de gasto (6 farmacias x 2 tipos) + 4 campos calculados
- **Vista form** con pestanas por farmacia
- Filtros por afiliado, anio, mes

### Proveedores y Liquidaciones (`provider_payments_views.xml`)

- CRUD de proveedores (nombre, tipo, % comision)
- Liquidaciones mensuales con boton "Generar Lineas"
- Vista de totales (importe plan, comision, a pagar, 40% farmacias)

### Reportes (`reports.xml`)

- **Reporte PDF** "Resumen Economico Mensual" con detalle de servicios
- **Template de email** enviado automaticamente al confirmar un registro
- **Accion automatizada** que dispara el envio del email cuando `state` cambia a `confirmed`

### Wizards

- **Filtro** (`payment_account_filter.xml`): Formulario con selector de periodo y estadisticas
- **Exportacion META4** (`meta_4_download.xml`): Formulario de dos pasos con descripcion de archivos y botones de descarga

---

## Menus

```
Administracion
├── Cuentas de Pago
│   ├── Mes Actual
│   ├── Crear Cuenta de Pago
│   ├── Filtrar Resumenes (wizard)
│   ├── Exportar Archivos Sindicales (wizard META4)
│   └── Resumen Economico (vista agrupada)
├── Farmacias, Afiliados y Gastos
│   ├── Crear Gasto Mensual
│   └── Gastos Farmacia Mensuales
├── Liquidaciones
│   ├── Liquidacion Mes Actual
│   ├── Todas las Liquidaciones
│   └── Proveedores
└── Basicos por Clase
```

---

## CRON (Tarea Programada)

**Archivo:** `views/automate_payment_creation_views.xml`

- **Nombre:** Create Monthly Payment Accounts
- **Frecuencia:** Cada mes, el dia 1 a las 00:00
- **Ejecucion:** Infinita (`numbercall=-1`)
- **Metodo:** `affiliate.payment_account.cron_create_monthly_records()`
- **Accion:** Crea registros de cuenta corriente para todos los afiliados activos

---

## Seguridad (ir.model.access.csv)

25 reglas de acceso para 8 modelos, con 3 niveles:

| Modelo | Admin (RWCD) | Write (RWC) | Read (R) |
|---|---|---|---|
| `affiliate.payment_account` | Si | Si | Si |
| `payment.account.filter.wizard` | Si | Si | Si |
| `payment.export.wizard` | Si | Si | Si |
| `affiliate.class.basic` | Si | Si | Si |
| `sindicato.proveedor` | Si | Si | Si |
| `sindicato.liquidacion.mensual` | Si | Si | Si |
| `sindicato.importe.mensual` | Si | Si | Si |
| `affiliate.pharmacy.expenses` | Si | Si | Si |

(R=Read, W=Write, C=Create, D=Delete)

---

## Flujos principales

### Creacion automatica de registros mensuales

```
Dia 1 del mes (CRON)
    └── cron_create_monthly_records()
            └── create_monthly_records_for_all_affiliates(mes, anio)
                    └── Para cada afiliado activo sin registro:
                            ├── Crea affiliate.payment_account
                            └── Crea affiliate.pharmacy.expenses
```

### Cascada de saldos

```
Se modifica un registro de Octubre
    └── _update_subsequent_months_initial_balance()
            ├── Noviembre.initial_balance = Octubre.final_balance
            ├── Diciembre.initial_balance = Noviembre.final_balance
            └── ... (todos los meses siguientes)
```

### Exportacion META4

```
Wizard Paso 1: Seleccionar mes/anio
    └── Wizard Paso 2: Generar archivos
            ├── Pagos Activos (concepto 7281)
            ├── Altas/Bajas (concepto 8522)
            ├── Cuota Sindical Activos (concepto 828)
            ├── Pagos Jubilados (concepto 7281)
            └── Cuota Sindical Jubilados (concepto 828)
```

---

## Historial de desarrollo (PRs mergeadas a `16.0`)

| PR | Fecha | Descripcion |
|---|---|---|
| #7 | Ago 2025 | Creacion del modulo de gestion economica |
| #9 | Ago 2025 | Correccion de error en menu de resumen |
| #13 | Sep 2025 | Metodos de generacion de archivos de salida |
| #15 | Sep 2025 | Limpieza de campos y metodos no usados |
| #24 | Sep 2025 | Correccion de comportamiento inconsistente de saldos |
| #25 | Sep 2025 | Correcciones menores (id/benefit, CUIL, nombres de campos) |
| #26 | Sep 2025 | Tabla de clases basicas y calculo de cuota sindical |
| #27 | Sep 2025 | Investigacion de envio de resumen economico por email |
| #38 | Oct 2025 | Modelo de pagos a proveedores |
| #39 | Oct 2025 | Modelo de farmacia |
| #40 | Oct 2025 | Edicion inline en vista de tabla |
| #41 | Oct 2025 | Cambios en basicos afectan solo mes actual en adelante |
| #42 | Oct 2025 | Inicializacion masiva de registros mensuales |
| #45/#46 | Oct 2025 | Permisos y carga batch en cuentas corrientes |
| #48 | Oct 2025 | Cambios menores |
| #50 | Oct 2025 | Generacion de archivos para jubilados |
| #52 | Oct 2025 | Saldo inicial editable en primer mes |
| #54 | Nov 2025 | Escala salarial basada solo en clase 1 |
| #56 | Nov 2025 | Filtro por nombre de afiliado |

---

## Estructura de archivos

```
road_union_economic_management/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── affiliate.py                # Extension del afiliado (id_benefit, creacion automatica)
│   ├── payment_account.py          # Cuenta corriente mensual + Clases salariales
│   ├── pharmacies.py               # Gastos de farmacia con descuento al 40%
│   └── provider_payments.py        # Proveedores, liquidaciones, importes mensuales
├── wizard/
│   ├── __init__.py
│   ├── payment_account_filter.py   # Filtro de cuentas corrientes por periodo
│   └── meta_4_download.py          # Exportacion de archivos META4
├── views/
│   ├── affiliate_views.xml                     # Herencia del form (id_benefit + pestana cuentas)
│   ├── payment_account_current_views.xml       # Vistas CRUD de cuentas corrientes
│   ├── payment_account_actions.xml             # Accion de resumen economico
│   ├── payment_account_filter.xml              # Wizard de filtro
│   ├── meta_4_download.xml                     # Wizard de exportacion
│   ├── affiliate_class_basic_views.xml         # CRUD de clases salariales
│   ├── pharmacies_views.xml                    # CRUD de gastos de farmacia
│   ├── provider_payments_views.xml             # CRUD de proveedores y liquidaciones
│   ├── reports.xml                             # Reporte PDF + email + accion automatizada
│   └── automate_payment_creation_views.xml     # CRON + search view
├── data/
│   ├── affiliate_class_basic_data.xml          # 20 clases salariales precargadas
│   └── pharmacies_data.xml                     # 6 farmacias precargadas
├── security/
│   └── ir.model.access.csv                     # 25 reglas de acceso (3 niveles)
└── static/
    └── description/
        └── icon.png                            # Icono del modulo
```
