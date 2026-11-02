"""Pruebas de seguridad y políticas de autorización en CargoBox."""

from src.cargobox.domain import EstadoEnvio
from src.cargobox.security import (
    puede_autorizar_cambio_direccion,
    puede_cancelar_envio,
    puede_dictaminar_indemnizacion,
)


def test_seguridad_atencion_clientes_puede_cambiar_direccion_en_transito():
    """Atención a Clientes sí puede autorizar cambio de dirección mientras esté en tránsito."""
    assert puede_autorizar_cambio_direccion(
        rol="ATENCION_CLIENTES",
        estado=EstadoEnvio.EN_TRANSITO.value,
    ) is True


def test_seguridad_repartidor_no_puede_autorizar_cambio_direccion():
    """Un repartidor no tiene permiso para autorizar cambios de dirección en el sistema."""
    assert puede_autorizar_cambio_direccion(
        rol="REPARTIDOR",
        estado=EstadoEnvio.EN_TRANSITO.value,
    ) is False


def test_seguridad_cambio_direccion_bloqueado_en_distribucion_destino():
    """Incluso Atención a Clientes tiene prohibido cambiar dirección si ya llegó al CEDIS destino."""
    assert puede_autorizar_cambio_direccion(
        rol="ATENCION_CLIENTES",
        estado=EstadoEnvio.EN_DISTRIBUCION_DESTINO.value,
    ) is False


def test_seguridad_empleado_sucursal_puede_cancelar_en_recibido():
    """Empleado de sucursal puede cancelar si el paquete sigue en RECIBIDO."""
    assert puede_cancelar_envio(
        rol="EMPLEADO_SUCURSAL",
        estado=EstadoEnvio.RECIBIDO.value,
    ) is True


def test_seguridad_empleado_sucursal_no_puede_cancelar_en_transito():
    """Ningún empleado puede cancelar un envío que ya se encuentra EN_TRANSITO."""
    assert puede_cancelar_envio(
        rol="EMPLEADO_SUCURSAL",
        estado=EstadoEnvio.EN_TRANSITO.value,
    ) is False


def test_seguridad_dictaminar_indemnizacion_roles():
    """Solo Supervisor y Gerente pueden dictaminar pagos de indemnización."""
    assert puede_dictaminar_indemnizacion("SUPERVISOR") is True
    assert puede_dictaminar_indemnizacion("GERENTE_OPERACIONES") is True
    assert puede_dictaminar_indemnizacion("REPARTIDOR") is False
    assert puede_dictaminar_indemnizacion("EMPLEADO_SUCURSAL") is False


def test_seguridad_cambio_direccion_bloqueado_en_regreso_a_centro():
    """Un paquete que regresó al centro tras 2 intentos ya no admite cambio de dirección."""
    assert puede_autorizar_cambio_direccion(
        rol="SUPERVISOR",
        estado=EstadoEnvio.REGRESO_CENTRO.value,
    ) is False


def test_seguridad_rol_no_autorizado_no_cancela():
    """Un repartidor no puede cancelar aunque el paquete siga en RECIBIDO."""
    assert puede_cancelar_envio(
        rol="REPARTIDOR",
        estado=EstadoEnvio.RECIBIDO.value,
    ) is False
