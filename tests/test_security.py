from datetime import UTC, datetime, timedelta

from src.security import can_cancel


def test_owner_within_24h():
    now = datetime.now(UTC)
    assert can_cancel("NEW", 1, 1, False, now - timedelta(hours=1), now)

def test_stranger_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 2, False, now, now)

def test_shipped_denied_even_admin():
    now = datetime.now(UTC)
    assert not can_cancel("SHIPPED", 1, 1, True, now, now)

def test_expired_denied():
    now = datetime.now(UTC)
    assert not can_cancel("NEW", 1, 1, False, now - timedelta(hours=25), now)

def test_admin_can_cancel_other_user_order():
    """Paso 6: Un administrador puede cancelar un pedido NEW de otro usuario."""
    now = datetime.now(UTC)
    created_at = now - timedelta(hours=10)
    assert can_cancel(
        status="NEW",
        owner_id=1,
        user_id=999,
        is_admin=True,
        created_at=created_at,
        now=now,
    )

def test_owner_exact_24h_boundary_denied():
    """Paso 6: Límite estricto de 24 horas. Exactamente a las 24h, la cancelación debe denegarse (< 24h)."""
    now = datetime.now(UTC)
    created_at = now - timedelta(hours=24)
    assert not can_cancel(
        status="NEW",
        owner_id=1,
        user_id=1,
        is_admin=False,
        created_at=created_at,
        now=now,
    )
