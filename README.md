# Actividad 5: Construcción de Lógica de Negocio y Pruebas Unitarias Automatizadas
* **Materia:** Componentes de Lógica de Negocios
* **Unidad:** 5
* **Equipo:** 14 (CargoBox)
* **Integrantes:** 
  * Pedro Omar Cardona Alvarez — Matrícula 2226579
  * Kloudenn Jafed Jiménez Valdivieso — Matrícula 2226639
  * Leonardo Acosta Morales — Matrícula 2226717

## Estructura del Proyecto

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

