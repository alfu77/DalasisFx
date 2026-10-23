import os
import tempfile
import pytest
from app import app
import database
from services.currency_service import convert_currency, validate_currency_code, fetch_exchange_rates

@pytest.fixture
def client():
    # Use a temporary SQLite database for testing
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    database.init_db(db_path=db_path)

    # Set temporary database path in database module
    old_db = database.DATABASE_PATH
    database.DATABASE_PATH = db_path

    with app.test_client() as client:
        yield client

    # Cleanup
    database.DATABASE_PATH = old_db
    os.close(db_fd)
    if os.path.exists(db_path):
        os.remove(db_path)

def test_index_page(client):
    """Test that the home dashboard loads correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Dalasi" in response.data
    assert b"Currency Exchange Calculator" in response.data

def test_api_currencies(client):
    """Test that /api/currencies returns supported currencies with GMD."""
    response = client.get("/api/currencies")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    codes = [c["code"] for c in data["currencies"]]
    assert "GMD" in codes
    assert "USD" in codes
    assert "EUR" in codes
    assert "GBP" in codes

def test_currency_validation():
    """Test ISO 3-letter currency code validation."""
    assert validate_currency_code("USD") is True
    assert validate_currency_code("gmd") is True
    assert validate_currency_code("EURO") is False
    assert validate_currency_code("123") is False
    assert validate_currency_code("") is False
    assert validate_currency_code(None) is False

def test_conversion_same_currency(client):
    """Converting from USD to USD should return rate 1.0."""
    response = client.get("/api/convert?from=USD&to=USD&amount=50")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["data"]["amount"] == 50.0
    assert data["data"]["result"] == 50.0
    assert data["data"]["rate"] == 1.0

def test_conversion_usd_to_gmd(client):
    """Test actual conversion from USD to Gambian Dalasi (GMD)."""
    response = client.get("/api/convert?from=USD&to=GMD&amount=100")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["data"]["from"] == "USD"
    assert data["data"]["to"] == "GMD"
    assert data["data"]["amount"] == 100.0
    assert data["data"]["result"] > 0
    assert data["data"]["rate"] > 0
    # Current market rate for 1 USD is between 50 and 100 GMD
    assert 40 < data["data"]["rate"] < 120

def test_conversion_invalid_inputs(client):
    """Test invalid amount and invalid currency codes."""
    # Negative amount
    resp1 = client.get("/api/convert?from=USD&to=GMD&amount=-10")
    assert resp1.status_code == 400

    # Non-numeric amount
    resp2 = client.get("/api/convert?from=USD&to=GMD&amount=abc")
    assert resp2.status_code == 400

    # Invalid currency code
    resp3 = client.get("/api/convert?from=INVALID&to=GMD&amount=10")
    assert resp3.status_code == 400

def test_conversion_rejects_non_finite_amounts(client):
    """NaN and infinity must not enter calculations or the conversion history."""
    for amount in ("nan", "inf", "-inf"):
        response = client.get(f"/api/convert?from=USD&to=GMD&amount={amount}")
        assert response.status_code == 400


def test_refresh_rejects_invalid_payload(client):
    """Refresh accepts a JSON object with a valid three-letter base code."""
    response = client.post("/api/refresh", json=["USD"])
    assert response.status_code == 400
    response = client.post("/api/refresh", json={"base": "INVALID"})
    assert response.status_code == 400

def test_popular_rates(client):
    """Test /api/popular returns benchmark cards."""
    response = client.get("/api/popular?base=USD")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    rates = data["data"]["popular_rates"]
    assert len(rates) > 0
    target_codes = [r["code"] for r in rates]
    assert "GMD" in target_codes

def test_conversion_history(client):
    """Test that conversions are logged in SQLite and retrieved via /api/history."""
    # Perform a conversion
    client.get("/api/convert?from=USD&to=GMD&amount=250")

    response = client.get("/api/history?limit=5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["conversions"]) >= 1
    recent = data["conversions"][0]
    assert recent["from_currency"] == "USD"
    assert recent["to_currency"] == "GMD"
    assert recent["amount"] == 250.0

def test_rate_snapshots_and_history(client):
    """Test snapshot recording and retrieval."""
    response = client.get("/api/rate-history?from=USD&to=GMD")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["base"] == "USD"
    assert data["target"] == "GMD"

def test_refresh_endpoint(client):
    """Test cache refresh endpoint."""
    response = client.post("/api/refresh", json={"base": "USD"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "refreshed successfully" in data["message"]
