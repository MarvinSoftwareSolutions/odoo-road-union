# road_union_affiliation - Documentacion

**Nombre en Odoo:** Sindicato vialidad - Afiliaciones
**Autor:** FMP solutions S.A.S. / Marvin Software Solutions
**Version:** 1.0
**Licencia:** AGPL-3
**Dependencias:** `base`, `union_affiliation`
**Branch principal:** `16.0`
**Repositorio:** MarvinSoftwareSolutions/odoo-road-union

---

## Proposito

Este modulo **extiende** el modulo base `union_affiliation` (desarrollado por terceros) con funcionalidades especificas para el **sindicato de vialidad de la provincia de Cordoba**. Agrega campos como obra social, departamento de trabajo, clase/categoria, calculo de edad, y logica de importacion masiva de familiares.

No crea un sistema nuevo, sino que hereda y amplia los modelos existentes de afiliacion, y agrega dos modelos propios de datos maestros (obra social y departamento).

---

## Modelos

### 1. `affiliation.affiliate` (extension del afiliado base)

**Archivo:** `models/affiliate.py`

Hereda el modelo `affiliation.affiliate` del modulo base y agrega:

| Campo | Tipo | Descripcion |
|---|---|---|
| `category` | Integer | Clase/categoria salarial del afiliado |
| `insurance_id` | Many2one → `affiliation.insurance` | Obra social (ondelete='restrict') |
| `department_id` | Many2one → `affiliation.department` | Departamento de trabajo (ondelete='restrict') |
| `age` | Integer (computed) | Edad calculada desde `birth_date`, no almacenada |
| `birthday_str` | Char (computed) | Cumpleanos en formato DD/MM |

**Metodos:**

- **`_compute_age()`** — Calcula la edad en anos desde `birth_date`, considerando si ya cumplio anos este ano.
- **`_compute_birthday_str()`** — Formatea la fecha de nacimiento como DD/MM.
- **`action_view_children()`** — Abre una ventana con la lista de hijos del afiliado en modo lectura. Usa las vistas readonly definidas en `affiliate_child_readonly_views.xml`.

---

### 2. `affiliation.affiliate_child` (extension de familiar a cargo)

**Archivo:** `models/affiliate_child.py`

Hereda el modelo `affiliation.affiliate_child` del modulo base y agrega:

| Campo | Tipo | Descripcion |
|---|---|---|
| `age` | Integer (computed, stored) | Edad calculada con `relativedelta` |
| `affiliate_parent_name` | Char | Campo auxiliar para importacion masiva (nombre del padre/madre) |

**Metodos:**

- **`_compute_age()`** — Calcula la edad usando `dateutil.relativedelta` para mayor precision. Se almacena en base de datos (`stored=True`).

- **`create(vals)`** — Override del metodo create. Si viene el campo `affiliate_parent_name`, busca al afiliado por nombre y vincula al hijo automaticamente. Luego asigna el `parent_role` del afiliado segun su genero.

- **`write(vals)`** — Override del metodo write. Si se modifican los `affiliate_ids`, actualiza el `parent_role` de los afiliados vinculados.

- **`_update_parent_role(affiliate)`** — Metodo privado que asigna el rol parental automaticamente:
  - Genero femenino → `mother`
  - Genero masculino/otro/no reporta → `father`
  - Solo actualiza si el `parent_role` esta vacio o en `no`.

- **`_get_affiliate_by_name(name)`** — Busca un afiliado por nombre exacto. Usado como helper en importaciones masivas.

---

### 3. `affiliation.insurance` (Obra Social)

**Archivo:** `models/insurance.py`

Modelo nuevo para gestionar las obras sociales disponibles.

| Campo | Tipo | Descripcion |
|---|---|---|
| `name` | Char (required) | Nombre de la obra social |
| `code` | Char | Codigo identificador |
| `active` | Boolean (default True) | Si esta activa |

**Datos precargados** (en `data/insurance_data.xml`):
- **Sancor** (codigo: SC)
- **Ninguno** (codigo: -)

---

### 4. `affiliation.department` (Departamento de Trabajo)

**Archivo:** `models/department.py`

Modelo nuevo para los departamentos de trabajo del sindicato de vialidad.

| Campo | Tipo | Descripcion |
|---|---|---|
| `name` | Char (required) | Nombre del departamento |
| `code` | Char | Codigo |
| `active` | Boolean (default True) | Si esta activo |
| `delegate_name` | Char | Nombre del delegado sindical del departamento |

---

## Vistas

### Formulario del afiliado (herencia)

**Archivo:** `views/affiliate_views.xml`

Hereda el formulario base del afiliado (`union_affiliation.union_affiliation_affiliate_form`) e inserta tres campos despues de `affiliate_type_id`:
- `category` (Clase)
- `insurance_id` (Obra social, sin opcion de crear ni abrir)
- `department_id` (Departamento, sin opcion de crear ni abrir)

### Vista "Base de datos de afiliados"

**Archivo:** `views/affiliate_old_db_views.xml`

Vista tipo tabla con todos los datos del afiliado en columnas, pensada para consulta rapida tipo planilla. Incluye:
- Datos personales (genero, documento, CUIL, cumpleanos, edad)
- Datos laborales (departamento, tipo, obra social, clase, antiguedad)
- Datos de contacto (direccion, telefono, celular)
- Boton "Ver Hijos" (icono fa-users, visible solo si tiene hijos)
- Filtro de busqueda por defecto: solo afiliados de tipo "Activo"

### Vistas de hijos (solo lectura)

**Archivo:** `views/affiliate_child_readonly_views.xml`

Vistas tree y form de solo lectura (`create="false"`, `edit="false"`, `delete="false"`) para consultar los familiares a cargo sin poder modificarlos. Se usan desde el boton "Ver Hijos" de la vista de afiliados.

Campos mostrados: nombre, edad, documento, fecha nacimiento, discapacidad, verificado, nivel educativo, observacion, nombres de afiliados padres.

### Vistas de Obra Social y Departamento

**Archivos:** `views/insurance_views.xml`, `views/department_views.xml`

CRUD estandar (tree + form) para gestionar obras sociales y departamentos respectivamente.

---

## Menus

El modulo renombra el menu raiz de `union_affiliation` a **"Administracion"** (en `views/menu.xml`) y agrega 4 items:

| Menu | Ubicacion | Accion |
|---|---|---|
| Obras Sociales | Administracion (raiz) | Lista de obras sociales |
| Departamentos | Administracion > Afiliados | Lista de departamentos |
| Base de Datos de Afiliados | Administracion > Afiliados | Vista tabla de afiliados (filtro Activos) |
| Hijos de Afiliados | Administracion > Afiliados | Vista readonly de hijos |

Todos los menus requieren el grupo `group_affiliation_read` como minimo.

---

## Seguridad (ir.model.access.csv)

Control de acceso en tres niveles, reutilizando los grupos del modulo base:

| Modelo | Admin | Write | Read |
|---|---|---|---|
| `affiliation.insurance` | RWCD | RWC | R |
| `affiliation.department` | RWCD | RWC | R |

(R=Read, W=Write, C=Create, D=Delete/Unlink)

---

## Historial de desarrollo (PRs mergeadas a `16.0`)

| PR | Fecha | Descripcion |
|---|---|---|
| #2 | Jul 2025 | Creacion del modulo. Agrega departamento, obra social y clase al afiliado |
| #5 | Jul 2025 | Vista de base de datos de afiliados (estilo planilla) |
| #28 | Sep 2025 | Vista de hijos con filtro por edad |
| #29 | Sep 2025 | Agrega nombre de delegado al departamento |
| #58 | Nov 2025 | Carga masiva de hijos por archivo, actualizacion automatica de rol parental |

---

## Estructura de archivos

```
road_union_affiliation/
├── __manifest__.py
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── affiliate.py            # Extension del afiliado (clase, obra social, departamento, edad)
│   ├── affiliate_child.py      # Extension de hijos (edad, importacion masiva, rol parental auto)
│   ├── department.py           # Modelo nuevo: departamentos de trabajo
│   └── insurance.py            # Modelo nuevo: obras sociales
├── views/
│   ├── menu.xml                # Renombra menu raiz a "Administracion"
│   ├── affiliate_views.xml     # Herencia del form de afiliado (3 campos nuevos)
│   ├── affiliate_old_db_views.xml      # Vista tabla completa de afiliados
│   ├── affiliate_child_readonly_views.xml  # Vistas readonly de hijos
│   ├── insurance_views.xml     # CRUD de obras sociales
│   └── department_views.xml    # CRUD de departamentos
├── data/
│   └── insurance_data.xml      # Datos iniciales: Sancor y Ninguno
└── security/
    └── ir.model.access.csv     # Permisos por grupo (admin/write/read)
```
