import pytest

from webapp.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    return app.test_client()


def test_hello_default(client):
    assert client.get("/hello").get_data(as_text=True) == "<h1>Hello, world!</h1>"


def test_hello_escapes_name(client):
    body = client.get("/hello?name=<b>x</b>").get_data(as_text=True)
    assert body == "<h1>Hello, &lt;b&gt;x&lt;/b&gt;!</h1>"


def test_link_quotes_and_escapes(client):
    body = client.get("/link", query_string={"q": "a b&<c>"}).get_data(as_text=True)
    assert body == '<a href="/search?q=a%20b%26%3Cc%3E">a b&amp;&lt;c&gt;</a>'
