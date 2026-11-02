"""Pruebas de servicio con dobles de prueba (Mocks) para CargoBox."""

from datetime import date
from unittest.mock import Mock

import pytest

from src.cargobox.application import EnvioAppService, ICentroDistribucionService
from src.cargobox.domain import (
    Direccion,
    Envio,
    EstadoEnvio,
    EvidenciaEntrega,
    Paquete,
    Seguro,
    SinEvidenciaEntregaException,
    TipoEvidencia,
    TipoIncidencia,
)


def test_envio_service_cedis_mock_exito():
    """Simula la consulta exitosa a un servicio externo de enrutamiento y CEDIS."""
    mock_service = Mock(spec=ICentroDistribucionService)
    mock_service.sugerir_centro_por_cp.return_value = "CEDIS_MONTERREY_NORTE"

    app_service = EnvioAppService(centro_service=mock_service)
    direccion = Direccion("Av. Universidad 1000", "San Nicolás", "66455")
    paquete = Paquete(peso_kg=2.0, descripcion="Documentos urgentes")

    envio = app_service.registrar_envio(
        guia="GUIA-MOCK-01",
        remitente="Notaría 12",
        destinatario="Corporativo Regio",
        direccion=direccion,
        paquete=paquete,
        costo_flete=220.0,
    )

    assert envio.centro_distribucion == "CEDIS_MONTERREY_NORTE"
    # Comprobar que el mock fue invocado exactamente una vez con el código postal
    mock_service.sugerir_centro_por_cp.assert_called_once_with("66455")


def test_envio_service_cedis_mock_timeout_fallback():
    """Simula una falla de red o timeout del servicio externo y comprueba resiliencia con fallback."""
    mock_service = Mock(spec=ICentroDistribucionService)
    # El servicio externo lanza una excepción (simulando timeout o caída de API)
    mock_service.sugerir_centro_por_cp.side_effect = TimeoutError("Connection to routing provider timed out")

    app_service = EnvioAppService(centro_service=mock_service)
    direccion = Direccion("Carretera Nacional Km 250", "Santiago", "67300")
    paquete = Paquete(peso_kg=10.0, descripcion="Herramientas")

    envio = app_service.registrar_envio(
        guia="GUIA-FALLBACK-02",
        remitente="Taller Mecánico",
        destinatario="Cliente Foráneo",
        direccion=direccion,
        paquete=paquete,
        costo_flete=450.0,
    )

    # El sistema no se cae: asigna el CEDIS regional por defecto
    assert envio.centro_distribucion == "CEDIS_REGIONAL_DEFAULT"
    mock_service.sugerir_centro_por_cp.assert_called_once_with("67300")


def test_envio_service_cancelar_coordina():
    """Verifica que el servicio de aplicación delega la cancelación al agregado."""
    app_service = EnvioAppService()
    envio = Envio(
        guia="GUIA-APP-03",
        remitente="Remitente A",
        destinatario="Destinatario B",
        direccion_destino=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Muestra textil"),
        costo_flete=180.0,
        estado=EstadoEnvio.RECIBIDO,
    )

    app_service.cancelar_envio(envio, motivo="Cancelación solicitada por remitente en ventanilla")
    assert envio.estado == EstadoEnvio.CANCELADO


def test_envio_service_reclamo_indemnizacion():
    """Verifica el cálculo de compensación para paquete con seguro."""
    app_service = EnvioAppService()
    envio = Envio(
        guia="GUIA-APP-04",
        remitente="Remitente A",
        destinatario="Destinatario B",
        direccion_destino=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Laptop"),
        costo_flete=300.0,
        seguro=Seguro(monto_declarado=18000.0, tiene_seguro=True),
        estado=EstadoEnvio.RECIBIDO,
    )

    monto = app_service.tramitar_reclamo_dano(envio, "dano_laptop.jpg")
    assert monto == 18000.0


def test_envio_service_registrar_intento_fallido():
    """Verifica que el servicio de aplicación delega el intento fallido al agregado."""
    app_service = EnvioAppService()
    envio = Envio(
        guia="GUIA-APP-05",
        remitente="Remitente A",
        destinatario="Destinatario B",
        direccion_destino=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Muestra"),
        costo_flete=150.0,
        estado=EstadoEnvio.EN_REPARTO,
    )
    app_service.registrar_intento_fallido(envio, TipoIncidencia.DESTINATARIO_AUSENTE)
    assert envio.intentos_entrega == 1
    assert envio.estado == EstadoEnvio.EN_DISTRIBUCION_DESTINO


def _envio_en(estado):
    return Envio(
        guia="GUIA-APP-06",
        remitente="Remitente A",
        destinatario="Destinatario B",
        direccion_destino=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Caja"),
        costo_flete=200.0,
        estado=estado,
    )


def test_envio_service_decision_en_centro_coordina():
    """El servicio delega la decisión del centro (US10) y fija la fecha de reprogramación."""
    app_service = EnvioAppService()
    envio = _envio_en(EstadoEnvio.EN_REPARTO)
    hoy = date(2026, 11, 2)
    app_service.registrar_intento_fallido(envio, TipoIncidencia.DESTINATARIO_AUSENTE, hoy)
    app_service.registrar_intento_fallido(envio, TipoIncidencia.DESTINATARIO_AUSENTE, hoy)
    assert envio.estado == EstadoEnvio.REGRESO_CENTRO
    app_service.resolver_reintento(envio, cobrar_reintento=True, hoy=hoy)
    assert envio.estado == EstadoEnvio.EN_DISTRIBUCION_DESTINO
    assert envio.fecha_reprogramacion == date(2026, 11, 3)


def test_envio_service_confirmar_entrega_exige_evidencia():
    """El servicio delega la entrega (US13): con evidencia entrega, sin ella falla."""
    app_service = EnvioAppService()
    sin = _envio_en(EstadoEnvio.EN_REPARTO)
    with pytest.raises(SinEvidenciaEntregaException):
        app_service.confirmar_entrega(sin, None)
    assert sin.estado == EstadoEnvio.EN_REPARTO

    con = _envio_en(EstadoEnvio.EN_REPARTO)
    app_service.confirmar_entrega(con, EvidenciaEntrega(TipoEvidencia.FOTO, "ok.jpg"))
    assert con.estado == EstadoEnvio.ENTREGADO


def test_envio_service_registrar_sin_centro_service_usa_cedis_local():
    """Sin servicio externo de CEDIS se asigna el CEDIS local de origen."""
    envio = EnvioAppService().registrar_envio(
        guia="GUIA-APP-07",
        remitente="Remitente A",
        destinatario="Destinatario B",
        direccion=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Caja"),
        costo_flete=100.0,
    )
    assert envio.centro_distribucion == "CEDIS_LOCAL_ORIGEN"
