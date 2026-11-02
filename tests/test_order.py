import pytest

from src.domain import CustomerHasDebt, Order


def test_vip_discount():
    o = Order(100, vip=True)
    assert o.confirm() == 85
    assert o.status == "CONFIRMED"

def test_regular_no_discount():
    assert Order(100).confirm() == 100

def test_vip_discount_200():
    """Paso 2: Pedido de 200 con cliente VIP recibe 15% de descuento ($30) y totaliza 170."""
    o = Order(200, vip=True)
    assert o.confirm() == 170
    assert o.discount == 30.0
    assert o.status == "CONFIRMED"

def test_regular_no_discount_200():
    """Paso 2: Pedido de 200 con cliente regular no recibe descuento y totaliza 200."""
    o = Order(200, vip=False)
    assert o.confirm() == 200
    assert o.discount == 0.0
    assert o.status == "CONFIRMED"

def test_cannot_confirm_twice():
    """Paso 3 (TDD): Un pedido ya confirmado no puede confirmarse una segunda vez."""
    order = Order(100)
    order.confirm()
    with pytest.raises(ValueError, match="already confirmed"):
        order.confirm()

def test_customer_debt():
    with pytest.raises(CustomerHasDebt):
        Order(100).confirm(customer_debt=50)

@pytest.mark.parametrize("total", [0, -1])
def test_invalid_total(total):
    with pytest.raises(ValueError):
        Order(total).confirm()
