"""CargoBox — Capa de aplicación (Application Service).

Coordina casos de uso integrando el modelo de dominio con servicios externos
(asignación de CEDIS por código postal) mediante Inversión de Dependencias (puertos y adaptadores).
"""

from datetime import date
from typing import Protocol

from src.cargobox.domain import (
    Direccion,
    Envio,
    EvidenciaEntrega,
    Paquete,
    Seguro,
    TipoIncidencia,
)


class ICentroDistribucionService(Protocol):
    """Puerto para servicio externo de geolocalización y asignación de CEDIS."""
    def sugerir_centro_por_cp(self, codigo_postal: str) -> str:
        ...


class EnvioAppService:
    def __init__(self, centro_service: ICentroDistribucionService | None = None):
        self.centro_service = centro_service

    def registrar_envio(
        self,
        guia: str,
        remitente: str,
        destinatario: str,
        direccion: Direccion,
        paquete: Paquete,
        costo_flete: float,
        seguro: Seguro | None = None,
    ) -> Envio:
        """Coordina el registro del paquete e invoca el servicio externo para sugerir CEDIS."""
        envio = Envio(
            guia=guia,
            remitente=remitente,
            destinatario=destinatario,
            direccion_destino=direccion,
            paquete=paquete,
            costo_flete=costo_flete,
            seguro=seguro or Seguro(),
        )

        if self.centro_service:
            try:
                cedis = self.centro_service.sugerir_centro_por_cp(direccion.codigo_postal)
                envio.centro_distribucion = cedis
            except (RuntimeError, TimeoutError, ConnectionError, OSError):
                # Estrategia de resiliencia: si el servicio externo falla o tiene timeout,
                # se asigna un centro regional predeterminado sin interrumpir la operación
                envio.centro_distribucion = "CEDIS_REGIONAL_DEFAULT"
        else:
            envio.centro_distribucion = "CEDIS_LOCAL_ORIGEN"

        return envio

    def registrar_intento_fallido(
        self, envio: Envio, motivo: TipoIncidencia, hoy: date | None = None
    ) -> None:
        """Coordina el registro de una visita infructuosa sobre el agregado."""
        envio.registrar_intento_fallido(motivo, hoy)

    def resolver_reintento(
        self, envio: Envio, cobrar_reintento: bool, hoy: date | None = None
    ) -> None:
        """Coordina la decisión del centro: cobrar reintento extra o devolver a origen."""
        envio.resolver_en_centro(cobrar_reintento, hoy)

    def confirmar_entrega(self, envio: Envio, evidencia: EvidenciaEntrega | None) -> None:
        """Coordina la entrega exigiendo la evidencia capturada en la app móvil."""
        envio.marcar_entregado(evidencia)

    def cancelar_envio(self, envio: Envio, motivo: str) -> None:
        """Coordina la cancelación del envío solicitando validación al dominio."""
        envio.cancelar(motivo)

    def tramitar_reclamo_dano(self, envio: Envio, foto_dano: str | None) -> float:
        """Evalúa la indemnización económica ante reporte de daño con fotografía."""
        return envio.evaluar_indemnizacion(foto_dano)
