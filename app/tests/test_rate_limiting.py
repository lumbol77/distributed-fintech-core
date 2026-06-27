import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def auth_headers(client):
    client.post("/users/", json={"email": "ratelimit_user@sentinel.com", "password": "RatePass123!"})
    res = client.post("/users/login", data={"username": "ratelimit_user@sentinel.com", "password": "RatePass123!"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestRateLimiting:
    def test_first_request_within_limit_is_allowed(self, client, auth_headers):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        with patch("app.core.rate_limiter.redis_client", mock_redis):
            with patch("app.services.transaction_service.check_fraud_with_resilience") as mock_fraud:
                mock_fraud.return_value = {"is_fraud": False, "reason": "api_eval_complete"}
                res = client.post("/wallets/wallet/transfer", json={"receiver_email": "anyone@sentinel.com", "amount": 10.0}, headers=auth_headers)
        assert res.status_code != 429

    def test_request_under_limit_is_allowed(self, client, auth_headers):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"3"
        with patch("app.core.rate_limiter.redis_client", mock_redis):
            with patch("app.services.transaction_service.check_fraud_with_resilience") as mock_fraud:
                mock_fraud.return_value = {"is_fraud": False, "reason": "api_eval_complete"}
                res = client.post("/wallets/wallet/transfer", json={"receiver_email": "anyone@sentinel.com", "amount": 10.0}, headers=auth_headers)
        assert res.status_code != 429

    def test_request_over_limit_returns_429(self, client, auth_headers):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"5"
        with patch("app.core.rate_limiter.redis_client", mock_redis):
            res = client.post("/wallets/wallet/transfer", json={"receiver_email": "anyone@sentinel.com", "amount": 10.0}, headers=auth_headers)
        assert res.status_code == 429

    def test_rate_limit_error_message(self, client, auth_headers):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"10"
        with patch("app.core.rate_limiter.redis_client", mock_redis):
            res = client.post("/wallets/wallet/transfer", json={"receiver_email": "anyone@sentinel.com", "amount": 10.0}, headers=auth_headers)
        assert res.status_code == 429
        assert "too many requests" in res.json()["detail"].lower()

    def test_rate_limit_counter_increments_on_each_request(self, client, auth_headers):
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"2"
        with patch("app.core.rate_limiter.redis_client", mock_redis):
            with patch("app.services.transaction_service.check_fraud_with_resilience") as mock_fraud:
                mock_fraud.return_value = {"is_fraud": False, "reason": "api_eval_complete"}
                client.post("/wallets/wallet/transfer", json={"receiver_email": "anyone@sentinel.com", "amount": 10.0}, headers=auth_headers)
        mock_redis.incr.assert_called_once()
