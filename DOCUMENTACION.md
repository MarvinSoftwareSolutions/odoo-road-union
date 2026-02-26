# odoo-road-union - Documentacion General

**Repositorio:** MarvinSoftwareSolutions/odoo-road-union
**Descripcion:** Modulos de Odoo 16 para la administracion del Sindicato de Vialidad de Cordoba
**Autor:** Marvin Software Solutions
**Licencia:** AGPL-3
**Branch principal:** `16.0`
**Todas las PRs se mergean a:** `16.0`

---

## Resumen

Este repositorio contiene **2 modulos de Odoo 16** desarrollados por Marvin Software Solutions para gestionar las operaciones de un sindicato de vialidad provincial. Ambos modulos extienden un modulo base de terceros (`union_affiliation` del repo `odoo-union`) que maneja la afiliacion sindical generica.

---

## Modulos

### 1. `road_union_affiliation` — Afiliaciones de Vialidad

**Extiende** el modulo base `union_affiliation` con datos especificos del sindicato de vialidad.

**Que agrega:**
- Campos en el afiliado: clase/categoria, obra social, departamento de trabajo, edad calculada
- Modelo de **Obra Social** (`affiliation.insurance`) con datos precargados (Sancor, Ninguno)
- Modelo de **Departamento** (`affiliation.department`) con nombre de delegado sindical
- Vista tipo planilla de la base de datos de afiliados (con boton "Ver Hijos")
- Vistas de solo lectura para consultar familiares a cargo
- Logica de importacion masiva de hijos con asignacion automatica de rol parental
- Menu renombrado a "Administracion"

**Documentacion detallada:** [`road_union_affiliation/DOCUMENTACION.md`](road_union_affiliation/DOCUMENTACION.md)

---

### 2. `road_union_economic_management` — Gestion Economica

Sistema integral de gestion economica del sindicato. Es el modulo mas complejo del repositorio.

**Que agrega:**
- **Cuentas corrientes mensuales** por afiliado con ~25 conceptos de servicios (farmacia, optica, odontologia, alojamientos, prestamos, turismo, etc.)
- **Cascada de saldos**: modificar un mes recalcula automaticamente todos los meses siguientes
- **Cuota sindical** calculada automaticamente segun clase salarial (diferenciada activos vs jubilados)
- **Gastos de farmacia** con 6 farmacias, descuento al 40% con tope acumulado de $125.000
- **Clases salariales basicas** (20 clases, todas calculadas a partir de clase 1)
- **Proveedores y liquidaciones mensuales** con calculo de comisiones
- **Exportacion META4**: wizard para generar archivos TXT de ancho fijo (conceptos 7281, 828, 8522) para integracion bancaria/previsional
- **Reporte PDF** y envio automatico por email al confirmar registros
- **CRON** que crea registros mensuales automaticamente el dia 1 de cada mes

**Documentacion detallada:** [`road_union_economic_management/DOCUMENTACION.md`](road_union_economic_management/DOCUMENTACION.md)

---

## Dependencias entre modulos

```
union_affiliation (repo odoo-union, modulo base de terceros)
    │
    └── road_union_affiliation (extension vialidad)
            │
            └── road_union_economic_management (gestion economica)
                    (tambien depende de base_automation)
```

Ambos modulos deben instalarse en orden. `road_union_economic_management` requiere que `road_union_affiliation` este instalado primero.

---

## Flujo de trabajo del desarrollo

- **Branch principal:** `16.0` (sigue la convencion de Odoo para la version)
- **Branch por issue:** Cada issue tiene su branch (ej: `57-massive-affiliates-childs-load`)
- **PRs a `16.0`:** Todas las PRs se mergean a la branch `16.0`
- **Nota:** Existe una branch `main` pero NO es la branch principal de desarrollo

---

## Issues

### Abiertas (pendientes)

| # | Titulo | Fecha |
|---|---|---|
| 59 | Fix pharmacy loads | Nov 2025 |
| 57 | Massive affiliate's childs load | Nov 2025 |
| 55 | Filter payment accounts by affiliate's name | Nov 2025 |
| 53 | Change salarial scale calculation using only class 1 | Nov 2025 |
| 51 | Modify initial balance in first month | Oct 2025 |
| 49 | Create retired files | Oct 2025 |
| 47 | Minor changes | Oct 2025 |
| 44 | Allow batch load to payment account model | Oct 2025 |
| 43 | Add wizards documentation | Oct 2025 |
| 36 | Initialize empty reports for current month for all affiliates | Sep 2025 |
| 35 | Check if changes in class basics modify the precalculated values | Sep 2025 |
| 34 | Edit payment values from tree view | Sep 2025 |
| 33 | Change colors in balance and payment | Sep 2025 |
| 32 | Pharmacy model | Sep 2025 |
| 31 | Add payment form model | Sep 2025 |
| 20 | Find out if payment fields can be added dynamically | Sep 2025 |
| 18 | Load meta4 file to data | Sep 2025 |
| 6 | Add separated permissions for economic management module | Ago 2025 |

**Nota:** Muchas issues figuran como "abiertas" pero ya tienen PR mergeada (ej: #57, #55, #53, #51, #49, #47, #44, #36, #35, #34, #32, #31). Faltaria cerrarlas.

### Cerradas

| # | Titulo |
|---|---|
| 37 | Edit payment account values from tree view |
| 30 | Rename Menu |
| 23 | Check for inconsistent balance behavior |
| 22 | Minor Corrections |
| 21 | Calculate union fee |
| 19 | Find out if payment account details can be sent to the affiliate |
| 17 | Children's view and age filter |
| 16 | Add union delegate to department |
| 14 | Create files for union fee, affiliates and pension |
| 11 | Add id/benefit in affiliate |
| 10 | Create files output methods |
| 8 | Solve error in summary menu |
| 4 | Add old db affiliates view |
| 3 | Create road_union_economic_management module |
| 1 | Add affiliate and child excel parameters on forms |

---

## Historial completo de PRs (mergeadas a `16.0`)

| PR | Fecha | Modulo | Descripcion |
|---|---|---|---|
| #2 | Jul 2025 | affiliation | Creacion del modulo. Departamento, obra social, clase |
| #5 | Ago 2025 | affiliation | Vista de base de datos de afiliados |
| #7 | Ago 2025 | economic | Creacion del modulo de gestion economica |
| #9 | Ago 2025 | economic | Correccion error en menu de resumen |
| #13 | Sep 2025 | economic | Metodos de generacion de archivos META4 |
| #15 | Sep 2025 | economic | Limpieza de campos y metodos no usados |
| #24 | Sep 2025 | economic | Correccion saldos inconsistentes |
| #25 | Sep 2025 | economic | Correcciones menores (id/benefit, CUIL, campos) |
| #26 | Sep 2025 | economic | Tabla de clases basicas y cuota sindical |
| #27 | Sep 2025 | economic | Envio de resumen economico por email |
| #28 | Sep 2025 | affiliation | Vista de hijos con filtro por edad |
| #29 | Sep 2025 | affiliation | Nombre de delegado en departamento |
| #38 | Oct 2025 | economic | Modelo de pagos a proveedores |
| #39 | Oct 2025 | economic | Modelo de farmacia |
| #40 | Oct 2025 | economic | Edicion inline en vista de tabla |
| #41 | Oct 2025 | economic | Basicos afectan solo mes actual en adelante |
| #42 | Oct 2025 | economic | Inicializacion masiva de registros mensuales |
| #45 | Oct 2025 | economic | Permisos de creacion en cuentas |
| #46 | Oct 2025 | economic | Carga batch en cuentas corrientes |
| #48 | Oct 2025 | economic | Cambios menores |
| #50 | Oct 2025 | economic | Archivos para jubilados |
| #52 | Oct 2025 | economic | Saldo inicial editable en primer mes |
| #54 | Nov 2025 | economic | Escala salarial basada en clase 1 |
| #56 | Nov 2025 | economic | Filtro por nombre de afiliado |
| #58 | Nov 2025 | affiliation | Carga masiva de hijos + rol parental automatico |

---

## Estructura del repositorio

```
odoo-road-union/
├── README.md
├── LICENSE (AGPL-3)
├── DOCUMENTACION.md                            # (este archivo)
├── road_union_affiliation/                     # Modulo de afiliaciones
│   ├── DOCUMENTACION.md
│   ├── __manifest__.py
│   ├── models/
│   │   ├── affiliate.py
│   │   ├── affiliate_child.py
│   │   ├── department.py
│   │   └── insurance.py
│   ├── views/ (6 archivos XML)
│   ├── data/ (insurance_data.xml)
│   └── security/ (ir.model.access.csv)
│
└── road_union_economic_management/             # Modulo de gestion economica
    ├── DOCUMENTACION.md
    ├── __manifest__.py
    ├── models/
    │   ├── affiliate.py
    │   ├── payment_account.py
    │   ├── pharmacies.py
    │   └── provider_payments.py
    ├── wizard/
    │   ├── payment_account_filter.py
    │   └── meta_4_download.py
    ├── views/ (10 archivos XML)
    ├── data/ (2 archivos XML)
    ├── security/ (ir.model.access.csv)
    └── static/description/icon.png
```
