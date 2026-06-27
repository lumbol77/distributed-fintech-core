import httpx
import asyncio
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models
from app.crud import wallet_crud as crud
from app.core.logging_config import logger, request_id_ctx
from app.core.tasks import send_transfer_notification
from app.core.metrics import TRANSACTION_COUNT, TRANSACTION_LATENCY

FRAUD_SERVICE_URL = "http://fraud-api:8001/predict"
MAX_RETRIES = 3
RETRY_DELAY = 1.0

async def check_fraud_with_resilience(user_id: int, amount: float):
    tx_id = request_id_ctx.get()
    payload = {"user_id": user_id, "amount": amount}
    headers = {"X-Request-ID": tx_id}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fraud check attempt {attempt + 1}/{MAX_RETRIES}")
                response = await client.post(FRAUD_SERVICE_URL, json=payload, headers=headers)
                response.raise_for_status()
                fraud_data = response.json()
                risk_score = fraud_data.get("risk_score")
                decision = fraud_data.get("decision")
                if risk_score is None or decision is None:
                    logger.warning(f"[{tx_id}] API Contract Mismatch. Activating fail-open.")
                    return {"is_fraud": False, "reason": "fail_open_contract_mismatch"}
                logger.info(f"[{tx_id}] Fraud Score: {risk_score} | Decision: {decision}")
                return {"is_fraud": decision == "block", "reason": "api_eval_complete"}
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                logger.warning(f"Fraud Service attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error(f"[{tx_id}] FAIL-SAFE: Fraud Service unreachable. Fail-Open: Allowing transaction.")
                    return {"is_fraud": False, "reason": "fail_open_service_unreachable"}
    return {"is_fraud": False, "reason": "fail_open_loop_exhausted"}

async def process_transfer(db: Session, sender: models.User, receiver_email: str, amount: float):
    tx_id = request_id_ctx.get()
    logger.info(f"Processing Transfer: {sender.email} -> {receiver_email} (${amount})")
    receiver = db.query(models.User).filter(models.User.email == receiver_email).with_for_update().first()
    if not receiver:
        logger.error(f"Transfer failed: Receiver {receiver_email} not found")
        raise HTTPException(status_code=404, detail="Receiver not found")
    fraud_result = await check_fraud_with_resilience(sender.id, amount)
    if fraud_result.get("is_fraud"):
        logger.warning(f"[{tx_id}] Sentinel Security: Transaction BLOCKED.")
        raise HTTPException(status_code=403, detail="Sentinel Security: Transaction blocked.")
    if "fail_open" in fraud_result.get("reason", ""):
        logger.info(f"[{tx_id}] Security Note: Transaction allowed via Fail-Open strategy.")
    try:
        db.query(models.Wallet).filter(models.Wallet.id==sender.wallet.id).with_for_update().first()
        result = crud.transfer_funds(db, sender.wallet.id, receiver_email, amount)
        send_transfer_notification.delay(
            sender_email=sender.email,
            receiver_email=receiver_email,
            amount=amount,
            tx_id=tx_id
        )
        TRANSACTION_COUNT.labels(status="success").inc()
        logger.info(f"SUCCESS: Transfer complete. Transaction ID: {tx_id}")
        return result
    except ValueError as e:
        logger.error(f"Transfer failed: {str(e)}")
        TRANSACTION_COUNT.labels(status="failed").inc()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected system error during transfer: {str(e)}", exc_info=True)
        TRANSACTION_COUNT.labels(status="failed").inc()
        raise HTTPException(status_code=500, detail="Internal Server Error")