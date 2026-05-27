import pytest
from app.routes import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"

def test_stocks_endpoint(client):
    resp = client.get("/stocks")
    assert resp.status_code == 200
    assert "available" in resp.json

def test_invalid_ticker(client):
    resp = client.get("/predict/AAPL")
    assert resp.status_code == 400

def test_predict_cba(client):
    resp = client.get("/predict/CBA.AX")
    assert resp.status_code == 200
    assert "predicted_close" in resp.json