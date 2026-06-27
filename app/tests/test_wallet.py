import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = "sqlite:///./test_wallet.db"
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def auth_headers(client):
    client.post("/users/", json={"email": "wallet_user@sentinel.com", "password": "WalletPass123!"})
    res = client.post("/users/login", data={"username": "wallet_user@sentinel.com", "password": "WalletPass123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestWalletBalance:
    def test_get_balance_authenticated_returns_200(self, client, auth_headers):
        res = client.get("/wallets/balance", headers=auth_headers)
        assert res.status_code == 200

    def test_new_wallet_balance_is_zero(self, client, auth_headers):
        res = client.get("/wallets/balance", headers=auth_headers)
        assert res.json()["balance"] == 0.0

    def test_get_balance_unauthenticated_returns_403(self, client):
        res = client.get("/wallets/balance")
        assert res.status_code in (401, 403)

class TestDeposit:
    def test_deposit_valid_amount_returns_200(self, client, auth_headers):
        res = client.post("/wallets/deposit", json={"amount": 500.0}, headers=auth_headers)
        assert res.status_code == 200

    def test_deposit_updates_balance(self, client, auth_headers):
        client.post("/wallets/deposit", json={"amount": 100.0}, headers=auth_headers)
        res = client.get("/wallets/balance", headers=auth_headers)
        assert res.json()["balance"] >= 100.0

    def test_deposit_response_contains_new_balance(self, client, auth_headers):
        res = client.post("/wallets/deposit", json={"amount": 50.0}, headers=auth_headers)
        data = res.json()
        assert "new_balance" in data
        assert data["new_balance"] > 0

    def test_deposit_without_auth_returns_403(self, client):
        res = client.post("/wallets/deposit", json={"amount": 100.0})
        assert res.status_code in (401, 403)

    def test_deposit_missing_amount_returns_422(self, client, auth_headers):
        res = client.post("/wallets/deposit", json={}, headers=auth_headers)
        assert res.status_code == 422

class TestWithdrawal:
    def test_withdraw_valid_amount_returns_200(self, client, auth_headers):
        client.post("/wallets/deposit", json={"amount": 300.0}, headers=auth_headers)
        res = client.post("/wallets/withdraw", json={"amount": 100.0}, headers=auth_headers)
        assert res.status_code == 200

    def test_withdraw_reduces_balance(self, client, auth_headers):
        client.post("/wallets/deposit", json={"amount": 200.0}, headers=auth_headers)
        before = client.get("/wallets/balance", headers=auth_headers).json()["balance"]
        client.post("/wallets/withdraw", json={"amount": 50.0}, headers=auth_headers)
        after = client.get("/wallets/balance", headers=auth_headers).json()["balance"]
        assert after == pytest.approx(before - 50.0, abs=0.01)

    def test_withdraw_insufficient_funds_returns_400(self, client, auth_headers):
        res = client.post("/wallets/withdraw", json={"amount": 999999.0}, headers=auth_headers)
        assert res.status_code == 400

    def test_withdraw_response_contains_new_balance(self, client, auth_headers):
        client.post("/wallets/deposit", json={"amount": 100.0}, headers=auth_headers)
        res = client.post("/wallets/withdraw", json={"amount": 10.0}, headers=auth_headers)
        assert "new_balance" in res.json()

    def test_withdraw_without_auth_returns_403(self, client):
        res = client.post("/wallets/withdraw", json={"amount": 10.0})
        assert res.status_code in (401, 403)
