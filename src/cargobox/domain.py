"""CargoBox — Modelo de dominio para gestión y rastreo de envíos y paquetería nacional.

Contiene las entidades, Value Objects, Aggregates y excepciones de negocio
según los requerimientos aprobados en las Unidades 2 y 3 (Equipo 14).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import Enum


class CargoBoxException(Exception):
    """Excepción base del dominio de CargoBox."""


class EnvioNoCancelableException(CargoBoxException):
    """Lanzada cuando se intenta cancelar un paquete que ya no está en sucursal."""


class MaximosIntentosExcedidosException(CargoBoxException):
    """Lanzada cuando se supera el límite de intentos de entrega permitidos (máx. 2)."""


class DireccionNoActualizableException(CargoBoxException):
    """Lanzada cuando se intenta cambiar la dirección habiendo arribado al centro destino."""


class DatosEnvioInvalidosException(CargoBoxException):
    """Lanzada cuando los datos del paquete o flete violan las invariantes del negocio."""


class SinEvidenciaEntregaException(CargoBoxException):
    """US13: lanzada cuando se intenta entregar sin foto o firma digital."""


class EntregaNoPermitidaException(CargoBoxException):
    """Lanzada cuando se intenta entregar un envío que no está en reparto."""


class SinEvidenciaDanoException(CargoBoxException):
    """US11: lanzada cuando el reporte de daño no incluye fotografía."""


class EnvioNoEnCentroException(CargoBoxException):
    """US10: lanzada cuando se decide sobre un envío que no regresó al centro."""


class EstadoEnvio(str, Enum):
    RECIBIDO = "RECIBIDO"
    EN_TRANSITO = "EN_TRANSITO"
    EN_DISTRIBUCION_DESTINO = "EN_DISTRIBUCION_DESTINO"
    EN_REPARTO = "EN_REPARTO"
    ENTREGADO = "ENTREGADO"
    CANCELADO = "CANCELADO"
    REGRESO_CENTRO = "REGRESO_CENTRO"
    DEVOLUCION_ORIGEN = "DEVOLUCION_ORIGEN"


class TipoIncidencia(str, Enum):
    DESTINATARIO_AUSENTE = "DESTINATARIO_AUSENTE"
    DIRECCION_INCORRECTA = "DIRECCION_INCORRECTA"
    PAQUETE_DANADO = "PAQUETE_DANADO"


class TipoEvidencia(str, Enum):
    FOTO = "FOTO"
    FIRMA_DIGITAL = "FIRMA_DIGITAL"


@dataclass(frozen=True)
class EvidenciaEntrega:
    """US13: evidencia capturada por el repartidor en la app móvil."""
    tipo: TipoEvidencia
    referencia: str

    def __post_init__(self):
        if not self.referencia.strip():
            raise DatosEnvioInvalidosException("La evidencia debe incluir un archivo o referencia")


@dataclass(frozen=True)
class Direccion:
    calle: str
    ciudad: str
    codigo_postal: str

    def __post_init__(self):
        if not self.calle.strip() or not self.ciudad.strip() or not self.codigo_postal.strip():
            raise DatosEnvioInvalidosException("Los datos de la dirección no pueden estar vacíos")


@dataclass(frozen=True)
class Seguro:
    monto_declarado: float = 0.0
    tiene_seguro: bool = False

    def __post_init__(self):
        if self.tiene_seguro and self.monto_declarado <= 0:
            raise DatosEnvioInvalidosException("Un envío con seguro debe tener monto declarado mayor a cero")
        if not self.tiene_seguro and self.monto_declarado > 0:
            raise DatosEnvioInvalidosException("No puede haber monto declarado si tiene_seguro es falso")


@dataclass(frozen=True)
class Paquete:
    peso_kg: float
    descripcion: str

    def __post_init__(self):
        if self.peso_kg <= 0:
            raise DatosEnvioInvalidosException("El peso del paquete debe ser estrictamente positivo")
        if self.peso_kg > 70.0:
            raise DatosEnvioInvalidosException("El peso del paquete no puede exceder el límite operativo de 70 kg")
        if not self.descripcion.strip():
            raise DatosEnvioInvalidosException("La descripción del contenido es obligatoria")


@dataclass
class Envio:
    """Aggregate Root que controla el ciclo de vida de un envío en CargoBox."""
    guia: str
    remitente: str
    destinatario: str
    direccion_destino: Direccion
    paquete: Paquete
    costo_flete: float
    seguro: Seguro = field(default_factory=Seguro)
    estado: EstadoEnvio = EstadoEnvio.RECIBIDO
    intentos_entrega: int = 0
    centro_distribucion: str | None = None
    fecha_creacion: datetime = field(default_factory=lambda: datetime.now(UTC))
    historial_incidencias: list[str] = field(default_factory=list)
    fecha_reprogramacion: date | None = None
    reintento_cobrado: bool = False
    evidencia_entrega: EvidenciaEntrega | None = None

    def __post_init__(self):
        if not self.guia.strip() or not self.remitente.strip() or not self.destinatario.strip():
            raise DatosEnvioInvalidosException("Guía, remitente y destinatario son obligatorios")
        if self.costo_flete <= 0:
            raise DatosEnvioInvalidosException("El costo del flete debe ser mayor a cero")

    # Regla 1: Cancelación de envío (US2)
    def cancelar(self, motivo: str) -> None:
        """Solo se puede cancelar un envío mientras siga físicamente en la sucursal de origen (RECIBIDO)."""
        if self.estado != EstadoEnvio.RECIBIDO:
            raise EnvioNoCancelableException(
                f"No se puede cancelar el envío {self.guia}: su estado actual es {self.estado.value}. "
                "Solo se permite cancelación cuando el paquete permanece en sucursal (RECIBIDO)."
            )
        if not motivo.strip():
            raise DatosEnvioInvalidosException("Se requiere un motivo para cancelar el envío")
        self.estado = EstadoEnvio.CANCELADO

    # Regla 2: Límite de intentos de entrega y reprogramación (US10)
    def registrar_intento_fallido(self, motivo: TipoIncidencia, hoy: date | None = None) -> None:
        """Registra una visita infructuosa (cliente ausente).

        Con menos de 2 intentos se reprograma para el día siguiente. Al llegar a 2 se detiene
        el reparto y el paquete regresa al centro de distribución (REGRESO_CENTRO) para decidir
        si se cobra un reintento extra o se devuelve a la sucursal de origen.
        """
        if self.intentos_entrega >= 2:
            raise MaximosIntentosExcedidosException(
                f"El envío {self.guia} ya alcanzó el límite máximo de 2 intentos permitidos."
            )

        hoy = hoy or date.today()
        self.intentos_entrega += 1
        self.historial_incidencias.append(f"Intento {self.intentos_entrega}: {motivo.value}")

        if self.intentos_entrega == 2:
            self.estado = EstadoEnvio.REGRESO_CENTRO
            self.fecha_reprogramacion = None
        else:
            self.estado = EstadoEnvio.EN_DISTRIBUCION_DESTINO
            self.fecha_reprogramacion = hoy + timedelta(days=1)

    def resolver_en_centro(self, cobrar_reintento: bool, hoy: date | None = None) -> None:
        """Decisión en el centro de distribución: cobrar reintento extra o devolver a origen."""
        if self.estado != EstadoEnvio.REGRESO_CENTRO:
            raise EnvioNoEnCentroException(
                f"El envío {self.guia} no está esperando decisión en el centro de distribución."
            )
        if cobrar_reintento:
            hoy = hoy or date.today()
            self.reintento_cobrado = True
            self.intentos_entrega = 0
            self.estado = EstadoEnvio.EN_DISTRIBUCION_DESTINO
            self.fecha_reprogramacion = hoy + timedelta(days=1)
        else:
            self.estado = EstadoEnvio.DEVOLUCION_ORIGEN

    # Regla 3: Actualización de dirección de entrega (US7)
    def actualizar_direccion(self, nueva_direccion: Direccion) -> None:
        """Solo se permite cambiar dirección antes de que el paquete llegue al centro de distribución destino final."""
        estados_permitidos = [EstadoEnvio.RECIBIDO, EstadoEnvio.EN_TRANSITO]
        if self.estado not in estados_permitidos:
            raise DireccionNoActualizableException(
                f"No se puede autorizar cambio de dirección: el envío ya se encuentra en '{self.estado.value}'."
            )
        self.direccion_destino = nueva_direccion

    # Regla 4: Evaluación de indemnización ante daño (US11, US12)
    def evaluar_indemnizacion(self, foto_dano: str | None) -> float:
        """Exige fotografía del daño. Con seguro paga el valor declarado; sin seguro, el flete."""
        if foto_dano is None or not foto_dano.strip():
            raise SinEvidenciaDanoException("El reporte de daño requiere fotografía del paquete")
        if self.seguro.tiene_seguro:
            return round(self.seguro.monto_declarado, 2)
        # Sin seguro: compensación limitada al reembolso del flete de envío
        return round(self.costo_flete, 2)

    # Regla 5: Prueba de recepción obligatoria (US13)
    def marcar_entregado(self, evidencia: EvidenciaEntrega | None) -> None:
        """Ningún paquete pasa a ENTREGADO sin foto o firma digital capturada por el repartidor."""
        if self.estado != EstadoEnvio.EN_REPARTO:
            raise EntregaNoPermitidaException(
                f"No se puede entregar el envío {self.guia}: su estado actual es {self.estado.value}."
            )
        if evidencia is None:
            raise SinEvidenciaEntregaException("Se requiere foto o firma digital para entregar")
        self.evidencia_entrega = evidencia
        self.estado = EstadoEnvio.ENTREGADO
