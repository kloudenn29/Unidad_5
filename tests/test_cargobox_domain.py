"""Pruebas unitarias de dominio para CargoBox (Paso 9: Adaptación a la empresa del PIA).

Cubre al menos 12 casos de prueba (éxito, error y límites) para las 4 reglas clave de CargoBox.
"""

from datetime import date

import pytest

from src.cargobox.domain import (
    DatosEnvioInvalidosException,
    Direccion,
    DireccionNoActualizableException,
    EntregaNoPermitidaException,
    Envio,
    EnvioNoCancelableException,
    EnvioNoEnCentroException,
    EstadoEnvio,
    EvidenciaEntrega,
    MaximosIntentosExcedidosException,
    Paquete,
    Seguro,
    SinEvidenciaDanoException,
    SinEvidenciaEntregaException,
    TipoEvidencia,
    TipoIncidencia,
)

HOY = date(2026, 11, 2)


def fixture_envio_base(estado=EstadoEnvio.RECIBIDO, tiene_seguro=False, monto_seguro=0.0):
    return Envio(
        guia="GUIA-CB-1001",
        remitente="Empresa Alfa",
        destinatario="Cliente Beta",
        direccion_destino=Direccion("Av. Insurgentes 123", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=5.0, descripcion="Refacciones automotrices"),
        costo_flete=350.0,
        seguro=Seguro(monto_declarado=monto_seguro, tiene_seguro=tiene_seguro),
        estado=estado,
    )


# === REGLA 1: Cancelación de Envíos (US2) ===

def test_cb01_cancelar_envio_en_sucursal_exito():
    """CP-01 (Éxito): Un envío en sucursal (RECIBIDO) puede cancelarse válidamente."""
    envio = fixture_envio_base(estado=EstadoEnvio.RECIBIDO)
    envio.cancelar(motivo="Cliente canceló la solicitud antes del despacho")
    assert envio.estado == EstadoEnvio.CANCELADO


def test_cb02_cancelar_envio_en_transito_error():
    """CP-02 (Error): Un envío que ya salió a tránsito (EN_TRANSITO) no puede cancelarse."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_TRANSITO)
    with pytest.raises(EnvioNoCancelableException, match="Solo se permite cancelación cuando el paquete permanece en sucursal"):
        envio.cancelar(motivo="Deseo cancelar el pedido en ruta")
    assert envio.estado == EstadoEnvio.EN_TRANSITO


def test_cb03_cancelar_sin_motivo_limite():
    """CP-03 (Límite/Error): La cancelación exige obligatoriamente un motivo no vacío."""
    envio = fixture_envio_base(estado=EstadoEnvio.RECIBIDO)
    with pytest.raises(DatosEnvioInvalidosException, match="Se requiere un motivo"):
        envio.cancelar(motivo="   ")
    assert envio.estado == EstadoEnvio.RECIBIDO


# === REGLA 2: Límite de Intentos de Entrega y Reprogramación (US10) ===

def test_cb04_primer_intento_fallido_reprograma():
    """CP-04 (Éxito): Ante cliente ausente en el intento 1, se programa nuevo intento."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE, HOY)
    assert envio.intentos_entrega == 1
    assert envio.estado == EstadoEnvio.EN_DISTRIBUCION_DESTINO
    assert envio.fecha_reprogramacion == date(2026, 11, 3)  # día siguiente
    assert len(envio.historial_incidencias) == 1


def test_cb05_segundo_intento_fallido_devolucion_limite():
    """CP-05 (Límite): Al 2do intento fallido se detiene el reparto y regresa al centro de distribución."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE)  # Intento 1
    envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE)  # Intento 2 (frontera)
    assert envio.intentos_entrega == 2
    assert envio.estado == EstadoEnvio.REGRESO_CENTRO
    assert envio.fecha_reprogramacion is None


def test_cb06_tercer_intento_fallido_bloqueado_error():
    """CP-06 (Error): Intentar registrar un 3er intento es rechazado por la regla de negocio."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE)
    envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE)
    with pytest.raises(MaximosIntentosExcedidosException, match="límite máximo de 2 intentos"):
        envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE)


# === REGLA 3: Actualización de Dirección de Entrega (US7) ===

def test_cb07_actualizar_direccion_en_transito_exito():
    """CP-07 (Éxito): Se permite cambio de dirección si el paquete aún no llega al CEDIS destino."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_TRANSITO)
    nueva = Direccion("Av. Constitución 456", "Monterrey", "64010")
    envio.actualizar_direccion(nueva)
    assert envio.direccion_destino == nueva


def test_cb08_actualizar_direccion_arribado_cedis_error():
    """CP-08 (Error): Arribado a EN_DISTRIBUCION_DESTINO, el cambio de dirección se bloquea."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_DISTRIBUCION_DESTINO)
    nueva = Direccion("Calle Nueva 789", "Monterrey", "64020")
    with pytest.raises(DireccionNoActualizableException, match="No se puede autorizar cambio de dirección"):
        envio.actualizar_direccion(nueva)


def test_cb09_direccion_vacia_limite():
    """CP-09 (Límite/Error): La dirección no admite campos vacíos o con espacios."""
    with pytest.raises(DatosEnvioInvalidosException, match="Los datos de la dirección no pueden estar vacíos"):
        Direccion("   ", "Monterrey", "64000")


# === REGLA 4: Evaluación de Seguro e Indemnización (US11, US12) ===

def test_cb10_indemnizacion_con_seguro_exito():
    """CP-10 (Éxito): Con seguro contratado, la indemnización cubre el monto total declarado."""
    envio = fixture_envio_base(tiene_seguro=True, monto_seguro=12500.0)
    indemnizacion = envio.evaluar_indemnizacion("dano_001.jpg")
    assert indemnizacion == 12500.0


def test_cb11_indemnizacion_sin_seguro_limite():
    """CP-11 (Límite): Sin seguro contratado, la indemnización se limita al costo del flete ($350)."""
    envio = fixture_envio_base(tiene_seguro=False, monto_seguro=0.0)
    indemnizacion = envio.evaluar_indemnizacion("dano_002.jpg")
    assert indemnizacion == 350.0


def test_cb12_peso_excedido_error():
    """CP-12 (Error/Límite): Paquete con peso mayor a 70 kg es rechazado por políticas de paquetería."""
    with pytest.raises(DatosEnvioInvalidosException, match="no puede exceder el límite operativo de 70 kg"):
        Paquete(peso_kg=70.1, descripcion="Caja extra pesada")


def test_cb13_seguro_invalido_monto_negativo():
    """Invariante: Seguro activo con monto <= 0 lanza excepción."""
    with pytest.raises(DatosEnvioInvalidosException, match="debe tener monto declarado mayor a cero"):
        Seguro(monto_declarado=0.0, tiene_seguro=True)


def test_cb14_seguro_invalido_monto_sin_flag():
    """Invariante: Monto declarado sin bandera de seguro activa lanza excepción."""
    with pytest.raises(DatosEnvioInvalidosException, match="No puede haber monto declarado si tiene_seguro es falso"):
        Seguro(monto_declarado=500.0, tiene_seguro=False)


def test_cb15_paquete_peso_cero_o_descripcion_vacia():
    """Invariante: Peso cero o negativo y descripción vacía lanzan excepción."""
    with pytest.raises(DatosEnvioInvalidosException, match="peso del paquete debe ser estrictamente positivo"):
        Paquete(peso_kg=0.0, descripcion="Prueba")
    with pytest.raises(DatosEnvioInvalidosException, match="descripción del contenido es obligatoria"):
        Paquete(peso_kg=1.0, descripcion="   ")


def test_cb16_envio_datos_obligatorios_y_flete_positivo():
    """Invariante: Guía vacía o flete <= 0 lanzan excepción."""
    dir_valida = Direccion("Calle 1", "Mty", "64000")
    paq_valido = Paquete(1.0, "Caja")
    with pytest.raises(DatosEnvioInvalidosException, match="Guía, remitente y destinatario son obligatorios"):
        Envio("", "Rem", "Dest", dir_valida, paq_valido, 100.0)
    with pytest.raises(DatosEnvioInvalidosException, match="costo del flete debe ser mayor a cero"):
        Envio("G1", "Rem", "Dest", dir_valida, paq_valido, -50.0)


# === REGLA 2 (continuación): Decisión en el centro de distribución (US10) ===

def test_cb17_centro_cobra_reintento_extra_reprograma():
    """CP-17 (Éxito): En el centro se cobra reintento extra: reinicia intentos y reprograma."""
    envio = fixture_envio_base(estado=EstadoEnvio.REGRESO_CENTRO)
    envio.intentos_entrega = 2
    envio.resolver_en_centro(cobrar_reintento=True, hoy=HOY)
    assert envio.reintento_cobrado is True
    assert envio.intentos_entrega == 0
    assert envio.estado == EstadoEnvio.EN_DISTRIBUCION_DESTINO
    assert envio.fecha_reprogramacion == date(2026, 11, 3)


def test_cb18_centro_devuelve_a_sucursal_origen():
    """CP-18 (Éxito): En el centro se decide no cobrar y el paquete se devuelve al origen."""
    envio = fixture_envio_base(estado=EstadoEnvio.REGRESO_CENTRO)
    envio.intentos_entrega = 2
    envio.resolver_en_centro(cobrar_reintento=False)
    assert envio.estado == EstadoEnvio.DEVOLUCION_ORIGEN
    assert envio.reintento_cobrado is False


def test_cb19_decision_en_centro_fuera_de_estado_error():
    """CP-19 (Error): No se puede decidir sobre un envío que no regresó al centro."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    with pytest.raises(EnvioNoEnCentroException):
        envio.resolver_en_centro(cobrar_reintento=True)
    assert envio.estado == EstadoEnvio.EN_REPARTO


# === REGLA 5: Prueba de recepción obligatoria (US13) ===

def test_cb20_entrega_con_foto_exito():
    """CP-20 (Éxito): Con fotografía como evidencia el envío pasa a ENTREGADO."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    evidencia = EvidenciaEntrega(TipoEvidencia.FOTO, "entrega_001.jpg")
    envio.marcar_entregado(evidencia)
    assert envio.estado == EstadoEnvio.ENTREGADO
    assert envio.evidencia_entrega == evidencia


def test_cb21_entrega_con_firma_digital_exito():
    """CP-21 (Éxito): La firma digital también es evidencia válida."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    envio.marcar_entregado(EvidenciaEntrega(TipoEvidencia.FIRMA_DIGITAL, "firma_001.png"))
    assert envio.estado == EstadoEnvio.ENTREGADO


def test_cb22_entrega_sin_evidencia_error():
    """CP-22 (Error): Sin evidencia el envío NO puede cambiar a ENTREGADO."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_REPARTO)
    with pytest.raises(SinEvidenciaEntregaException, match="foto o firma digital"):
        envio.marcar_entregado(None)
    assert envio.estado == EstadoEnvio.EN_REPARTO
    assert envio.evidencia_entrega is None


def test_cb23_evidencia_con_referencia_vacia_limite():
    """CP-23 (Límite): Una evidencia sin archivo o referencia es inválida."""
    with pytest.raises(DatosEnvioInvalidosException, match="debe incluir un archivo"):
        EvidenciaEntrega(TipoEvidencia.FOTO, "   ")


def test_cb24_entrega_fuera_de_reparto_error():
    """CP-24 (Error): No se entrega un envío que aún está en tránsito, aunque tenga evidencia."""
    envio = fixture_envio_base(estado=EstadoEnvio.EN_TRANSITO)
    with pytest.raises(EntregaNoPermitidaException):
        envio.marcar_entregado(EvidenciaEntrega(TipoEvidencia.FOTO, "x.jpg"))
    assert envio.estado == EstadoEnvio.EN_TRANSITO


# === REGLA 4 (continuación): Fotografía obligatoria del daño (US11) ===

@pytest.mark.parametrize("foto", [None, "   "])
def test_cb25_reclamo_sin_fotografia_error(foto):
    """CP-25 (Error): Un reporte de daño sin fotografía no se evalúa, ni con seguro."""
    envio = fixture_envio_base(tiene_seguro=True, monto_seguro=12500.0)
    with pytest.raises(SinEvidenciaDanoException, match="requiere fotografía"):
        envio.evaluar_indemnizacion(foto)
