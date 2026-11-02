"""CargoBox — Políticas de seguridad y autorización para operaciones de paquetería.

Implementa control de acceso basado en roles (RBAC) y estados de negocio
para asegurar que solo personal calificado autorice excepciones.
"""

from src.cargobox.domain import EstadoEnvio


def puede_autorizar_cambio_direccion(rol: str, estado: str) -> bool:
    """Solo Atención a Clientes o Supervisor pueden autorizar cambios de dirección,

    y únicamente antes de que el envío alcance el centro de distribución destino.
    """
    roles_autorizados = ["ATENCION_CLIENTES", "SUPERVISOR"]
    estados_bloqueados = [
        EstadoEnvio.EN_DISTRIBUCION_DESTINO.value,
        EstadoEnvio.EN_REPARTO.value,
        EstadoEnvio.REGRESO_CENTRO.value,
        EstadoEnvio.ENTREGADO.value,
        EstadoEnvio.CANCELADO.value,
        EstadoEnvio.DEVOLUCION_ORIGEN.value,
    ]

    if rol not in roles_autorizados:
        return False
    return estado not in estados_bloqueados


def puede_cancelar_envio(rol: str, estado: str) -> bool:
    """Solo Empleado de Sucursal o Supervisor pueden cancelar envíos que aún estén en sucursal (RECIBIDO)."""
    roles_autorizados = ["EMPLEADO_SUCURSAL", "SUPERVISOR"]
    if rol not in roles_autorizados:
        return False
    return estado == EstadoEnvio.RECIBIDO.value


def puede_dictaminar_indemnizacion(rol: str) -> bool:
    """Solo personal de nivel Supervisor o Gerente de Operaciones puede aprobar indemnizaciones."""
    return rol in ["SUPERVISOR", "GERENTE_OPERACIONES"]
