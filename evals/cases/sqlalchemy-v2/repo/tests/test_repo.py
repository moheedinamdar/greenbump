import pytest

from userdb.repo import add_user, count_users, make_engine, user_names


@pytest.fixture
def engine(tmp_path):
    return make_engine(f"sqlite:///{tmp_path / 'users.db'}")


def test_empty_database(engine):
    assert count_users(engine) == 0
    assert user_names(engine) == []


def test_add_and_list_users(engine):
    add_user(engine, "bob", "bob@example.com")
    add_user(engine, "alice", "alice@example.com")
    assert user_names(engine) == ["alice", "bob"]


def test_count_users(engine):
    add_user(engine, "carol", "carol@example.com")
    assert count_users(engine) == 1
