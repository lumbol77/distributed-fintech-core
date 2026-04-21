import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base, engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch # <--- Added for Mocking

# 1. Setup a Temporary Test Database
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture
def auth_header():
    # 1. Create the user
    client.post("/users/", json={"email": "testuser@gmail.com", "password": "password123"})
    
    # 2. Login
    login_response = client.post("/users/login", json={
        "email": "testuser@gmail.com", 
        "password": "password123"
    })
    
    token = login_response.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

# --- THE ACTUAL TESTS ---

def test_deposit(auth_header):
    response = client.post("/wallet/deposit", json={"amount": 1000}, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["new_balance"] == 1000

def test_insufficient_funds(auth_header):
    response = client.post("/wallet/withdraw", json={"amount": 5000}, headers=auth_header)
    assert response.status_code == 400
    # Match the exact error message from your crud.py
    assert "Insufficient" in response.json()["detail"]

# --- MOCKING THE AI CHECK ---
# We 'patch' the function in app.routers.wallet where it is USED
@patch("app.routers.wallet.check_fraud_risk") 
def test_atomic_transfer_logic(mock_fraud_check, auth_header):
    # 1. Tell the mock to ALWAYS return False (Not Fraud) for this test
    mock_fraud_check.return_value = False
    
    # 2. Setup Receiver
    client.post("/users/", json={"email": "receiver@gmail.com", "password": "password123"})
    
    # 3. Deposit into Sender
    client.post("/wallet/deposit", json={"amount": 1000}, headers=auth_header)
    
    # 4. Transfer
    response = client.post("/wallet/transfer", json={
        "receiver_email": "receiver@gmail.com",
        "amount": 400
    }, headers=auth_header)
    
    assert response.status_code == 200
    assert response.json()["new_balance"] == 600
    # Verify the AI was actually called once
    assert mock_fraud_check.called

@patch("app.routers.wallet.check_fraud_risk")
def test_blocked_by_fraud_ai(mock_fraud_check, auth_header):
    # 1. Tell the mock to return True (SIMULATE FRAUD)
    mock_fraud_check.return_value = True
    
    client.post("/users/", json={"email": "receiver@gmail.com", "password": "password123"})
    client.post("/wallet/deposit", json={"amount": 1000}, headers=auth_header)

    response = client.post("/wallet/transfer", json={
        "receiver_email": "receiver@gmail.com",
        "amount": 400
    }, headers=auth_header)

    # Should be blocked with 403
    assert response.status_code == 403
    assert "flagged" in response.json()["detail"].lower()