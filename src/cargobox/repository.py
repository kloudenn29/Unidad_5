"""CargoBox — Capa de persistencia con SQLAlchemy.

Separa el modelo de dominio de la base de datos mediante el patrón Repository
y gestiona transacciones con Session (Unit of Work).
"""


from sqlalchemy import Boolean, Column, Date, Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session

from src.cargobox.domain import Envio


class CargoBoxBase(DeclarativeBase):
    pass


class EnvioRow(CargoBoxBase):
    __tablename__ = "cargobox_envios"

    guia = Column(String, primary_key=True)
    remitente = Column(String, nullable=False)
    destinatario = Column(String, nullable=False)
    codigo_postal = Column(String, nullable=False)
    costo_flete = Column(Float, nullable=False)
    estado = Column(String, nullable=False)
    intentos_entrega = Column(Integer, default=0, nullable=False)
    tiene_seguro = Column(Boolean, default=False, nullable=False)
    monto_declarado = Column(Float, default=0.0, nullable=False)
    centro_distribucion = Column(String, nullable=True)
    fecha_reprogramacion = Column(Date, nullable=True)
    reintento_cobrado = Column(Boolean, default=False, nullable=False)
    evidencia_tipo = Column(String, nullable=True)
    evidencia_referencia = Column(String, nullable=True)


class SqlEnvioRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, envio: Envio) -> None:
        row = EnvioRow(
            guia=envio.guia,
            remitente=envio.remitente,
            destinatario=envio.destinatario,
            codigo_postal=envio.direccion_destino.codigo_postal,
            costo_flete=envio.costo_flete,
            estado=envio.estado.value,
            intentos_entrega=envio.intentos_entrega,
            tiene_seguro=envio.seguro.tiene_seguro,
            monto_declarado=envio.seguro.monto_declarado,
            centro_distribucion=envio.centro_distribucion,
            fecha_reprogramacion=envio.fecha_reprogramacion,
            reintento_cobrado=envio.reintento_cobrado,
            evidencia_tipo=envio.evidencia_entrega.tipo.value if envio.evidencia_entrega else None,
            evidencia_referencia=(
                envio.evidencia_entrega.referencia if envio.evidencia_entrega else None
            ),
        )
        self.session.add(row)

    def get_by_guia(self, guia: str) -> EnvioRow | None:
        return self.session.scalar(select(EnvioRow).where(EnvioRow.guia == guia))


def make_cargobox_engine(url: str = "sqlite+pysqlite:///:memory:"):
    engine = create_engine(url)
    CargoBoxBase.metadata.create_all(engine)
    return engine
