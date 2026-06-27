import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock

FRAUD_API_URL = "http://localhost:8001"

def fraud_service_available():
    try:
        r = httpx.get(f"{FRAUD_API_URL}/", timeout=2.0)
        return r.status_code < 500
    except httpx.RequestError:
        return False

live_only = pytest.mark.skipif(not fraud_service_available(), reason="fraud-api not reachable")

class TestFraudAPIContract:
    @live_only
    def test_predict_endpoint_returns_200(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1, "amount": 100.0})
        assert res.status_code == 200

    @live_only
    def test_predict_response_contains_risk_score(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1, "amount": 100.0})
        assert "risk_score" in res.json()

    @live_only
    def test_predict_response_contains_decision(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1, "amount": 100.0})
        data = res.json()
        assert "decision" in data
        assert data["decision"] in ("allow", "block")

    @live_only
    def test_predict_risk_score_is_float_between_0_and_1(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1, "amount": 100.0})
        score = res.json()["risk_score"]
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @live_only
    def test_high_amount_triggers_response(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1, "amount": 999999.0})
        assert res.status_code == 200
        assert "decision" in res.json()

    @live_only
    def test_predict_missing_fields_returns_422(self):
        res = httpx.post(f"{FRAUD_API_URL}/predict", json={"user_id": 1})
        assert res.status_code == 422

class TestFraudResilienceLayer:
    @pytest.mark.asyncio
    async def test_allow_decision_returns_is_fraud_false(self):
        from app.services.transaction_service import check_fraud_with_resilience
        mock_response = MagicMock()
        mock_response.json.return_value = {"risk_score": 0.1, "decision": "allow"}
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await check_fraud_with_resilience(user_id=1, amount=100.0)
        assert result["is_fraud"] is False

    @pytest.mark.asyncio
    async def test_block_decision_returns_is_fraud_true(self):
        from app.services.transaction_service import check_fraud_with_resilience
        mock_response = MagicMock()
        mock_response.json.return_value = {"risk_score": 0.95, "decision": "block"}
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await check_fraud_with_resilience(user_id=1, amount=50000.0)
        assert result["is_fraud"] is True

    @pytest.mark.asyncio
    async def test_service_unreachable_triggers_fail_open(self):
        from app.services.transaction_service import check_fraud_with_resilience
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.RequestError("Connection refused")):
            result = await check_fraud_with_resilience(user_id=1, amount=100.0)
        assert result["is_fraud"] is False
        assert "fail_open" in result["reason"]

    @pytest.mark.asyncio
    async def test_contract_mismatch_triggers_fail_open(self):
        from app.services.transaction_service import check_fraud_with_resilience
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected_field": "garbage"}
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await check_fraud_with_resilience(user_id=1, amount=100.0)
        assert result["is_fraud"] is False
        assert result["reason"] == "fail_open_contract_mismatch"

    @pytest.mark.asyncio
    async def test_http_status_error_triggers_fail_open(self):
        from app.services.transaction_service import check_fraud_with_resilience
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())):
            result = await check_fraud_with_resilience(user_id=1, amount=100.0)
        assert result["is_fraud"] is False
        assert "fail_open" in result["reason"]
