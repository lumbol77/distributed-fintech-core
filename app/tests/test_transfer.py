import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_TEST_URL = 'sqlite:///./test_transfer.db'
engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope='module', autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:
        yield c

def _register_and_login(client, email, password='TestPass123!'):
    client.post('/users/', json={'email': email, 'password': password})
    res = client.post('/users/login', data={'username': email, 'password': password})
    token = res.json()['access_token']
    return {'Authorization': f'Bearer {token}'}

@pytest.fixture(scope='module')
def sender_headers(client):
    headers = _register_and_login(client, 'sender@sentinel.com')
    client.post('/wallets/deposit', json={'amount': 1000.0}, headers=headers)
    return headers

@pytest.fixture(scope='module')
def receiver_headers(client):
    return _register_and_login(client, 'receiver@sentinel.com')

def _clear_rate_limit():
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    return mock_redis

class TestTransfer:
    def test_transfer_valid_returns_200(self, client, sender_headers, receiver_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 100.0}, headers=sender_headers)
        assert res.status_code == 200

    def test_transfer_response_contains_new_balance(self, client, sender_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 50.0}, headers=sender_headers)
        assert 'new_balance' in res.json()

    def test_transfer_deducts_sender_balance(self, client, sender_headers):
        before = client.get('/wallets/balance', headers=sender_headers).json()['balance']
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 75.0}, headers=sender_headers)
        after = client.get('/wallets/balance', headers=sender_headers).json()['balance']
        assert after == pytest.approx(before - 75.0, abs=0.01)

    def test_transfer_credits_receiver_balance(self, client, sender_headers, receiver_headers):
        before = client.get('/wallets/balance', headers=receiver_headers).json()['balance']
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 25.0}, headers=sender_headers)
        after = client.get('/wallets/balance', headers=receiver_headers).json()['balance']
        assert after == pytest.approx(before + 25.0, abs=0.01)

    def test_transfer_to_nonexistent_user_returns_404(self, client, sender_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'ghost@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.status_code == 404

    def test_transfer_insufficient_funds_returns_400(self, client, sender_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
                res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 999999.0}, headers=sender_headers)
        assert res.status_code == 400

    def test_transfer_blocked_by_fraud_returns_403(self, client, sender_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': True, 'reason': 'api_eval_complete'}):
                res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.status_code == 403

    def test_transfer_without_auth_returns_403(self, client):
        res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0})
        assert res.status_code in (401, 403)

    def test_transfer_missing_amount_returns_422(self, client, sender_headers):
        with patch('app.core.rate_limiter.redis_client', _clear_rate_limit()):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com'}, headers=sender_headers)
        assert res.status_code == 422

class TestTransactionHistory:
    def test_get_history_returns_200(self, client, sender_headers):
        res = client.get('/wallets/transactions', headers=sender_headers)
        assert res.status_code == 200

    def test_history_returns_list(self, client, sender_headers):
        res = client.get('/wallets/transactions', headers=sender_headers)
        assert isinstance(res.json(), list)

    def test_history_entries_have_correct_fields(self, client, sender_headers):
        res = client.get('/wallets/transactions', headers=sender_headers)
        entries = res.json()
        if entries:
            entry = entries[0]
            assert 'id' in entry
            assert 'amount' in entry
            assert 'type' in entry
            assert 'timestamp' in entry

    def test_history_without_auth_returns_403(self, client):
        res = client.get('/wallets/transactions')
        assert res.status_code in (401, 403)
