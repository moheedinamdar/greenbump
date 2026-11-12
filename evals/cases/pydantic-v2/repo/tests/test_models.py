import json

import pytest
from pydantic import ValidationError

from inventory.models import Item, Order


def make_item(**overrides):
    data = {"sku": "ABC-1234", "name": " Widget ", "price": 2.5, "quantity": 4}
    data.update(overrides)
    return Item(**data)


def test_item_name_is_stripped():
    assert make_item().name == "Widget"


def test_sku_pattern_is_enforced():
    with pytest.raises(ValidationError):
        make_item(sku="bad-sku")


def test_blank_name_is_rejected():
    with pytest.raises(ValidationError):
        make_item(name="   ")


def test_negative_price_is_rejected():
    with pytest.raises(ValidationError):
        make_item(price=-1)


def test_order_note_is_optional():
    order = Order(order_id=1, items=[make_item()])
    assert order.note is None


def test_order_total():
    order = Order(order_id=1, items=[make_item(), make_item(quantity=2)], note=None)
    assert order.total() == 15.0


def test_order_json_is_pretty_and_sorted():
    order = Order(order_id=7, items=[make_item()], note="rush")
    text = order.to_json()
    assert text.startswith("{\n  ")
    data = json.loads(text)
    assert list(data) == sorted(data)
    assert list(data["items"][0]) == sorted(data["items"][0])
    assert data["items"][0]["sku"] == "ABC-1234"
