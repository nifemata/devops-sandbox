import pytest

from app.main import add, app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_add_function():
    assert add(2, 3) == 5


def test_index_reports_version(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.get_json()
    assert body["message"].startswith("Hello")
    assert "version" in body


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_add_route(client):
    assert client.get("/add?a=1.5&b=2").get_json() == {"result": 3.5}


def test_add_route_rejects_text(client):
    assert client.get("/add?a=x&b=2").status_code == 400
