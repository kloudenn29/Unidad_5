from unittest.mock import Mock

import pytest

from src.application import OrderService
from src.domain import Order


def test_gateway_approved():
    gateway = Mock()
    gateway.charge.return_value = True
    assert OrderService(gateway).checkout(Order(100)) == 100
    gateway.charge.assert_called_once_with(100)

def test_gateway_rejected():
    gateway = Mock()
    gateway.charge.return_value = False
    with pytest.raises(RuntimeError):
        OrderService(gateway).checkout(Order(100))

def test_gateway_rejected_vip_order():
    """Paso 5: Pedido VIP de $200 (monto con descuento = $170); si pasarela rechaza, lanza RuntimeError."""
    gateway = Mock()
    gateway.charge.return_value = False
    vip_order = Order(200, vip=True)

    with pytest.raises(RuntimeError, match="payment rejected"):
        OrderService(gateway).checkout(vip_order)

    # Verifica que intentó cobrar exactamente el monto con descuento VIP (200 - 15% = 170)
    gateway.charge.assert_called_once_with(170.0)
