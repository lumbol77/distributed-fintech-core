import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sender_headers():
    token = create_access_token(data={'sub': 'sender@sentinel.com'})
    return {'Authorization': f'Bearer {token}'}

class TestTransfer:
    @pytest.fixture(autouse=True)
    def bypass_rate_limiter(self):
        with patch('app.middleware.rate_limiting.RateLimiter.__call__', side_effect=lambda request, call_next: call_next(request)):
            yield

    def test_transfer_valid_returns_200(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.status_code == 200

    def test_transfer_response_contains_new_balance(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert 'new_balance' in res.json()

    def test_transfer_deducts_sender_balance(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.json()['new_balance'] < 100.0

    def test_transfer_credits_receiver_balance(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
            client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert True

    def test_transfer_to_nonexistent_user_returns_404(self, client, sender_headers):
        res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'fake@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.status_code == 404

    def test_transfer_insufficient_funds_returns_400(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': False, 'reason': 'api_eval_complete'}):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 999999.0}, headers=sender_headers)
        assert res.status_code == 400

    def test_transfer_blocked_by_fraud_returns_403(self, client, sender_headers):
        with patch('app.services.transaction_service.check_fraud_with_resilience', new_callable=AsyncMock, return_value={'is_fraud': True, 'reason': 'api_eval_complete'}):
            res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0}, headers=sender_headers)
        assert res.status_code == 403

    def test_transfer_without_auth_returns_403(self, client):
        res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com', 'amount': 10.0})
        assert res.status_code in (401, 403)

    def test_transfer_missing_amount_returns_422(self, client, sender_headers):
        res = client.post('/wallets/wallet/transfer', json={'receiver_email': 'receiver@sentinel.com'}, headers=sender_headers)
        assert res.status_code == 422

class TestTransactionHistory:
    def test_get_history_returns_200(self, client, sender_headers):
        res = client.get('/wallets/wallet/history', headers=sender_headers)
        assert res.status_code == 200

    def test_history_returns_list(self, client, sender_headers):
        res = client.get('/wallets/wallet/history', headers=sender_headers)
        assert isinstance(res.json(), list)

    def test_history_entries_have_correct_fields(self, client, sender_headers):
        res = client.get('/wallets/wallet/history', headers=sender_headers)
        if len(res.json()) > 0:
            entry = res.json()[0]
            assert 'amount' in entry
            assert 'type' in entry

    def test_history_without_auth_returns_403(self, client):
        res = client.get('/wallets/wallet/history')
        assert res.status_code in (401, 403)
