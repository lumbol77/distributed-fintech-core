from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models, crud
from app.utils import check_fraud_risk

async def process_transfer(db: Session, sender: models.User, receiver_email: str, amount: float):
    # 1. Find receiver
    receiver = db.query(models.User).filter(models.User.email == receiver_email).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    # 2. Check for Fraud (The Security Mission)
    is_fraud = await check_fraud_risk(
        amount=amount, 
        sender_balance=sender.wallet.balance,
        receiver_balance=receiver.wallet.balance
    )
    
    if is_fraud:
        raise HTTPException(status_code=403, detail="Sentinel Security: Transaction blocked.")

    # 3. Execute the actual transfer in the DB
    try:
        return crud.wallet_crud.transfer_funds(db, sender.wallet.id, receiver_email, amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))