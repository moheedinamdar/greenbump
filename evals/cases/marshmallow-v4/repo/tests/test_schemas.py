import pytest
from marshmallow import ValidationError

from accounts.schemas import dump_user, load_user


def test_load_applies_default_role():
    user = load_user({"name": "Ada", "email": "ada@example.com"})
    assert user == {"name": "Ada", "email": "ada@example.com", "role": "viewer"}


def test_load_rejects_short_name():
    with pytest.raises(ValidationError) as info:
        load_user({"name": "A", "email": "a@example.com"})
    assert info.value.messages == {"name": ["Name is too short."]}


def test_dump_fills_active_and_display():
    out = dump_user({"name": "Ada", "email": "ada@example.com", "role": "admin"}, prefix="Dr. ")
    assert out == {
        "name": "Ada",
        "email": "ada@example.com",
        "role": "admin",
        "active": True,
        "display": "Dr. Ada",
    }


def test_dump_without_prefix():
    out = dump_user({"name": "Ada", "email": "ada@example.com", "role": "admin", "active": False})
    assert out["display"] == "Ada"
    assert out["active"] is False
