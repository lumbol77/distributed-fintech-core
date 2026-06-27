from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app import schemas
from app.security import get_current_user
from app.database import get_db
from app.crud import wallet_crud as crud
from app.services import transaction_service
from app.services.wallet_service import deposit_service, withdraw_service, get_transaction_history
from app.core.rate_limiter import rate_limit_user
from app.core.tasks import send_transfer_notification

router = APIRouter(tags=["Wallet"])

@router.get("/balance")
def get_wallet_balance(current_user=Depends(get_current_user)):
    return {"balance": current_user.wallet.balance}

@router.post("/deposit")
def deposit_money(
    request: schemas.DepositRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    updated_wallet = deposit_service(db, current_user.wallet.id, request.amount)
    return {"message": "Deposit successful", "new_balance": updated_wallet.balance}

@router.post("/withdraw")
def withdraw_money(
    request: schemas.WithdrawRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        updated_wallet = withdraw_service(db, current_user.wallet.id, request.amount)
        return {"message": "Withdrawal successful", "new_balance": updated_wallet.balance}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/wallet/test-queue")
async def test_queue(
    sender_id: int = 1,
    receiver_email: str = "test@example.com",
    amount: float = 100.0,
):
    send_transfer_notification.delay(
        sender_email="system@sentinel.com",
        receiver_email=receiver_email,
        amount=amount,
        tx_id=0,
    )
    return {"status": "success", "message": "Celery job pushed to Redis broker successfully"}

@router.post("/wallet/transfer")
async def transfer_money(
    request: schemas.TransferRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _=Depends(rate_limit_user),
):
    updated_wallet = await transaction_service.process_transfer(
        db, current_user, request.receiver_email, request.amount
    )
    send_transfer_notification.delay(
        sender_email=current_user.email,
        receiver_email=request.receiver_email,
        amount=request.amount,
        tx_id=updated_wallet.id,
    )
    return {
        "message": "Transfer successful",
        "new_balance": updated_wallet.balance,
    }

@router.get("/transactions", response_model=list[schemas.TransactionResponse])
def get_history(
    transaction_type: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_transaction_history(db, current_user.wallet.id, transaction_type)
