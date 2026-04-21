from sqlalchemy.orm import Session
from app.crud import wallet_crud as crud
def deposit_service(db: Session, wallet_id: int, amount: float):
    """
    Handles deposit logic.
    (Right now simple, later can include validation, logging, etc.)
    """
    return crud.deposit_funds(db, wallet_id, amount)
def withdraw_service(db: Session, wallet_id: int, amount: float):
    """
    Handles withdraw logic with validation.
    """
    return crud.withdraw_funds(db, wallet_id, amount)

def get_transaction_history(db: Session, wallet_id: int, transaction_type: str):
    return crud.get_transactions(db, wallet_id, transaction_type)