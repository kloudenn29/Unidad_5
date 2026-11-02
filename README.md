# Actividad 5: Construcción de Lógica de Negocio y Pruebas Unitarias Automatizadas
**Materia:** Construcción de Lógica de Negocio (CLN)  
**Equipo:** 14 — Proyecto PIA: **CargoBox** (Logística y Envíos Express)  

---

## 1. Alcance de la Tarea y Arquitectura

De acuerdo con las especificaciones de la **Guía de Laboratorio Unidad 5** y el archivo `README-UNIDAD5-CLN.docx`, la actividad se divide en dos componentes integrados en esta misma solución:

1. **Laboratorio Base (Pasos 1 al 8):**
   - Dominio de comercio electrónico (`Order`, `OrderItem`).
   - Ciclo TDD: implementación de la regla de no recompra/doble confirmación (`test_cannot_confirm_twice`).
   - Persistencia transaccional con SQLAlchemy y SQLite (`SqlOrderRepository`), validando `commit` y aislamiento en caso de error.
   - Integración simulada (Mocks) con pasarela de pagos externa (`IPaymentGateway`), probando escenarios exitosos y de rechazo de cobro.
   - Matriz de control de acceso basada en roles (RBAC) y ventana de tiempo para cancelaciones (regla estricta: ningún rol puede cancelar pedidos ya enviados).

2. **Transferencia al Proyecto PIA CargoBox (Paso 9):**
   - Dominio logístico integral (`Envio`, `Direccion`, `Seguro`, `Paquete`, `EstadoEnvio`).
   - Implementación de 4 reglas de negocio críticas del PIA:
     * **Regla 1 (US2):** Cancelación permitida únicamente en sucursal (`RECIBIDO`). Una vez en tránsito (`EN_TRANSITO`), queda estrictamente prohibida la cancelación.
     * **Regla 2 (US10):** Gestión de intentos de entrega: 1er intento reprograma a CEDIS; 2do intento alcanza el límite y detona retorno a origen (`DEVOLUCION_ORIGEN`); un 3er intento es rechazado con excepción de dominio.
     * **Regla 3 (US7):** Actualización de dirección de entrega autorizada únicamente antes de que el paquete arribe al CEDIS destino.
     * **Regla 4 (US11/US12):** Dictaminación de indemnizaciones: paquetes asegurados recuperan hasta el 100% del valor declarado; paquetes estándar sin seguro están topados al costo del flete ($350 MXN).
   - Servicio de aplicación (`EnvioAppService`) con mock de servicio externo (`ICentroDistribucionService`) y resiliencia ante caídas de red.
   - Repositorio relacional SQLAlchemy (`SqlEnvioRepository`) con soporte completo de transacciones atómicas (`commit` / `rollback`).
   - Políticas de seguridad y autorización (`security.py`).

---

## 2. Estructura del Proyecto

```text
ACT5/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Pipeline CI/CD para compilación, ruff y pytest
├── datos/
│   └── matriz_casos_cargobox.csv      # Matriz de casos de prueba CargoBox (12 casos diseñados)
├── docs/
│   ├── Laboratorio_Guiado_Unidad_5_RESUELTO.docx # Reporte Word listo con tablas, respuestas y espacios para capturas
│   ├── Laboratorio_Guiado_Unidad_5_RESUELTO.md   # Reporte completo en formato Markdown
│   └── matriz_casos_cargobox.csv      # Copia para entrega directa de la matriz
├── htmlcov/                           # Reporte visual HTML de cobertura generado por pytest-cov
├── src/
│   ├── __init__.py
│   ├── domain.py                      # Dominio del laboratorio base (Order)
│   ├── repository.py                  # Repositorio SQLAlchemy para Order
│   ├── service.py                     # Servicio de pago y confirmación con Mocks
│   ├── security.py                    # Políticas RBAC del laboratorio base
│   └── cargobox/                      # Dominio completo del PIA CargoBox
│       ├── __init__.py
│       ├── domain.py                  # Entidades, Value Objects, Enums y Excepciones de CargoBox
│       ├── repository.py              # Repositorio SQLAlchemy SqlEnvioRepository
│       ├── application.py             # EnvioAppService y protocolo ICentroDistribucionService
│       └── security.py                # Reglas de autorización y perfiles para CargoBox
├── tests/
│   ├── __init__.py
│   ├── test_order.py                  # Pruebas unitarias de dominio Order (TDD)
│   ├── test_repository.py             # Pruebas de persistencia Order
│   ├── test_service.py                # Pruebas con unittest.mock para pasarela de pago
│   ├── test_security.py               # Pruebas de seguridad y roles Order
│   ├── test_cargobox_domain.py        # 16 pruebas unitarias de las 4 reglas de negocio de CargoBox
│   ├── test_cargobox_repository.py    # Pruebas de persistencia y rollback de CargoBox
│   ├── test_cargobox_service.py       # Pruebas con Mocks de servicios de CEDIS
│   └── test_cargobox_security.py      # Pruebas de autorización RBAC de CargoBox
├── cargar_datos_demo.py               # Script para poblar la base SQLite de demostración
├── generar_docx_resuelto.py           # Generador automatizado del documento Word oficial
├── pyproject.toml                     # Configuración de pytest, coverage y ruff
├── requirements.txt                   # Dependencias requeridas
└── README.md                          # Este archivo de documentación
```

---

## 3. Instrucciones de Ejecución

### 3.1. Requisitos Previos y Entorno Virtual
El entorno virtual ya se encuentra configurado en la carpeta `.venv` con Python 3.11.

Para activarlo en Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

O en Bash / CMD:
```bash
.venv\Scripts\activate
```

Instalación de dependencias (si se ejecuta en otro equipo):
```bash
pip install -r requirements.txt
```

### 3.2. Ejecutar la Suite de Pruebas Automatizadas y Cobertura
Para correr las 49 pruebas unitarias y de integración junto con el análisis de cobertura:
```bash
pytest -v --cov=src --cov-report=term-missing --cov-report=html --cov-fail-under=80
```

**Resultado obtenido:**
- **49 pruebas pasadas exitosamente** (0 fallos, 0 errores).
- **Cobertura total: 99.04%** (superando con holgura el umbral mínimo del 80% exigido por la rúbrica).

### 3.3. Análisis Estático de Código (Linter)
Para validar el cumplimiento de estándares PEP 8 y buenas prácticas:
```bash
ruff check src tests
```
*Resultado:* `All checks passed!` (0 advertencias, 0 errores).

### 3.4. Carga de Datos Demo
Para recrear la base de datos SQLite local `pedidos_prueba.sqlite3`:
```bash
python cargar_datos_demo.py
```

### 3.5. Regenerar el Reporte Word (.docx)
Si deseas regenerar el archivo `docs/Laboratorio_Guiado_Unidad_5_RESUELTO.docx`:
```bash
python generar_docx_resuelto.py
```

---

## 4. Resumen de Pruebas Unitarias Desarrolladas

| Módulo de Prueba | Cantidad | Casos Clave Evaluados |
| :--- | :---: | :--- |
| `tests/test_order.py` | 6 | Descuento VIP, descuento regular, totalización, validación TDD de doble confirmación (`test_cannot_confirm_twice`). |
| `tests/test_repository.py` | 3 | Persistencia con SQLite en memoria, confirmación de estado persistido y prueba del pedido adicional solicitado en la guía. |
| `tests/test_service.py` | 5 | Mocks de pasarela externa: cobro exitoso, llamada correcta con monto con descuento, y manejo de rechazo con rollback. |
| `tests/test_security.py` | 10 | Matriz RBAC completa: usuario regular, administrador, pedidos propios vs ajenos, límite temporal exacto de 24 horas y pedidos enviados. |
| `tests/test_cargobox_domain.py` | 16 | Las 4 reglas de CargoBox: cancelación en sucursal vs tránsito, 1er/2do intento de entrega y desborde en el 3ero, cambio de dirección antes/después de CEDIS, e indemnización con y sin póliza. |
| `tests/test_cargobox_repository.py` | 3 | Persistencia real con SQLAlchemy para `cargobox_envios`, commit atómico y aislamiento en rollback. |
| `tests/test_cargobox_service.py` | 3 | Mocks para `ICentroDistribucionService`: asignación inteligente de CEDIS, y degradación elegante a CEDIS por defecto ante fallas de red. |
| `tests/test_cargobox_security.py` | 3 | Verificación de permisos de rol para cancelación, redirección e indemnización. |
| **Total** | **49** | **100% superadas con 99.04% de cobertura de código.** |

---

## 5. Entregables en la Carpeta `docs/`

1. **`docs/Laboratorio_Guiado_Unidad_5_RESUELTO.docx`**: Documento en formato Word oficial con todas las tablas llenas, respuestas analíticas a las preguntas de reflexión de los Pasos 1 al 9, extractos de código y recuadros grises destacados con la etiqueta `[ESPACIO PARA CAPTURA DE PANTALLA]` listos para pegar las capturas de ejecución.
2. **`docs/Laboratorio_Guiado_Unidad_5_RESUELTO.md`**: Versión completa en Markdown para lectura o visualización directa en el IDE / GitHub.
3. **`docs/matriz_casos_cargobox.csv`**: Matriz detallada en formato CSV con los casos de prueba de éxito, error y límite para el sistema CargoBox.
