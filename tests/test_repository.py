from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain import Order
from src.repository import OrderRow, SqlOrderRepository, make_engine


def test_repository_commit():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.commit()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)).total == 120

def test_repository_rollback():
    engine = make_engine()
    with Session(engine) as session:
        SqlOrderRepository(session).save(1, Order(120))
        session.rollback()
        assert session.scalar(select(OrderRow).where(OrderRow.id == 1)) is None

def test_repository_commit_order_2():
    """Paso 4: Guarda pedido id=2 con total 250, hace commit y verifica id, total y estado."""
    engine = make_engine()
    with Session(engine) as session:
        order = Order(250)
        order.confirm()
        SqlOrderRepository(session).save(2, order)
        session.commit()

        saved = session.scalar(select(OrderRow).where(OrderRow.id == 2))
        assert saved is not None
        assert saved.id == 2
        assert saved.total == 250.0
        assert saved.status == "CONFIRMED"
