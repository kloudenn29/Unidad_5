"""Pruebas de persistencia y límites transaccionales para CargoBox (SQLAlchemy + SQLite)."""

from datetime import date

from sqlalchemy.orm import Session

from src.cargobox.domain import (
    Direccion,
    Envio,
    EstadoEnvio,
    EvidenciaEntrega,
    Paquete,
    Seguro,
    TipoEvidencia,
    TipoIncidencia,
)
from src.cargobox.repository import SqlEnvioRepository, make_cargobox_engine


def test_cargobox_repository_commit():
    """Verifica que un envío persistido con commit() es visible en la base de datos."""
    engine = make_cargobox_engine()
    with Session(engine) as session:
        repo = SqlEnvioRepository(session)
        envio = Envio(
            guia="GUIA-PERSIST-01",
            remitente="Logística Norte",
            destinatario="Distribuidora Sur",
            direccion_destino=Direccion("Av. Revolución 100", "Guadalajara", "44100"),
            paquete=Paquete(peso_kg=3.5, descripcion="Componentes electrónicos"),
            costo_flete=280.0,
            seguro=Seguro(monto_declarado=5000.0, tiene_seguro=True),
            estado=EstadoEnvio.RECIBIDO,
        )
        repo.save(envio)
        session.commit()

        # Comprobar recuperación en la misma base
        recuperado = repo.get_by_guia("GUIA-PERSIST-01")
        assert recuperado is not None
        assert recuperado.guia == "GUIA-PERSIST-01"
        assert recuperado.remitente == "Logística Norte"
        assert recuperado.costo_flete == 280.0
        assert recuperado.estado == "RECIBIDO"
        assert recuperado.tiene_seguro is True
        assert recuperado.monto_declarado == 5000.0


def test_cargobox_repository_rollback():
    """Verifica que un rollback() descarta la transacción y no almacena registros."""
    engine = make_cargobox_engine()
    with Session(engine) as session:
        repo = SqlEnvioRepository(session)
        envio = Envio(
            guia="GUIA-ROLLBACK-02",
            remitente="Tienda Virtual",
            destinatario="Comprador Final",
            direccion_destino=Direccion("Calle Juárez 50", "Puebla", "72000"),
            paquete=Paquete(peso_kg=1.0, descripcion="Libro de texto"),
            costo_flete=150.0,
            seguro=Seguro(),
            estado=EstadoEnvio.RECIBIDO,
        )
        repo.save(envio)
        session.rollback()

        # Debe ser nulo tras el rollback
        recuperado = repo.get_by_guia("GUIA-ROLLBACK-02")
        assert recuperado is None


def _envio(guia, estado):
    return Envio(
        guia=guia,
        remitente="Remitente",
        destinatario="Destinatario",
        direccion_destino=Direccion("Calle 1", "Monterrey", "64000"),
        paquete=Paquete(peso_kg=1.0, descripcion="Caja"),
        costo_flete=100.0,
        estado=estado,
    )


def test_cargobox_repository_persiste_evidencia_de_entrega():
    """US13: la evidencia de entrega se guarda junto con el estado ENTREGADO."""
    engine = make_cargobox_engine()
    with Session(engine) as session:
        repo = SqlEnvioRepository(session)
        envio = _envio("GUIA-ENTREGA-03", EstadoEnvio.EN_REPARTO)
        envio.marcar_entregado(EvidenciaEntrega(TipoEvidencia.FOTO, "entrega_03.jpg"))
        repo.save(envio)
        session.commit()
        fila = repo.get_by_guia("GUIA-ENTREGA-03")
        assert fila.estado == "ENTREGADO"
        assert (fila.evidencia_tipo, fila.evidencia_referencia) == ("FOTO", "entrega_03.jpg")


def test_cargobox_repository_persiste_reprogramacion():
    """US10: se guarda la fecha de reprogramación del día siguiente tras el primer ausente."""
    engine = make_cargobox_engine()
    with Session(engine) as session:
        repo = SqlEnvioRepository(session)
        envio = _envio("GUIA-REPROG-04", EstadoEnvio.EN_REPARTO)
        envio.registrar_intento_fallido(TipoIncidencia.DESTINATARIO_AUSENTE, date(2026, 11, 2))
        repo.save(envio)
        session.commit()
        fila = repo.get_by_guia("GUIA-REPROG-04")
        assert fila.fecha_reprogramacion == date(2026, 11, 3)
        assert fila.intentos_entrega == 1
