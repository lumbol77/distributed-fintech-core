from sqlalchemy.orm import Session
from app import models, utils
from app import schemas 
from app.schemas import UserCreate, UserResponse, UserLogin, Token
def create_user_with_wallet(db: Session, user: schemas.UserCreate):
    """
    Creates a user and their associated wallet in one atomic operation.
    """
    # 1. Hash the password using our utils
    hashed_pw = utils.hash_password(user.password)

    # 2. Create User
    new_user = models.User(
        email=user.email,
        hashed_password=hashed_pw
    )
    db.add(new_user)
    db.flush() # Flush gives us the user.id without committing yet

    # 3. Create Wallet
    new_wallet = models.Wallet(user_id=new_user.id, balance=0.0)
    db.add(new_wallet)
    
    # 4. Commit both at once
    db.commit()
    db.refresh(new_user)
    return new_user

def deposit_funds(db: Session, wallet_id: int, amount: float):
    # Use begin_nested for safe sub-transactions (savepoints)
    with db.begin_nested():
        wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
        wallet.balance += amount
        db.add(models.Transaction(amount=amount, type="deposit", wallet_id=wallet_id))
    db.commit()
    return wallet

def withdraw_funds(db: Session, wallet_id: int, amount: float):
    with db.begin_nested():
        wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
        if wallet.balance < amount:
            raise ValueError("Insufficient funds")
            
        wallet.balance -= amount
        db.add(models.Transaction(amount=amount, type="withdrawal", wallet_id=wallet_id))
    db.commit()
    return wallet

def transfer_funds(db: Session, sender_wallet_id: int, receiver_email: str, amount: float):
    with db.begin_nested():
        # 1. Lock Sender Wallet
        sender_wallet = db.query(models.Wallet).filter(models.Wallet.id == sender_wallet_id).with_for_update().first()
        
        # 2. Get Receiver Wallet via Email Join
        receiver_wallet = db.query(models.Wallet).join(models.User).filter(models.User.email == receiver_email).with_for_update().first()
        
        if not receiver_wallet:
            raise ValueError("Receiver not found")
        if sender_wallet.id == receiver_wallet.id:
            raise ValueError("You cannot transfer to yourself")
        if sender_wallet.balance < amount:
            raise ValueError("Insufficient funds")

        # 3. Atomic Balance Swap
        sender_wallet.balance -= amount
        receiver_wallet.balance += amount

        # 4. Double-Entry Ledger Record
        db.add(models.Transaction(amount=amount, type="transfer_sent", wallet_id=sender_wallet.id))
        db.add(models.Transaction(amount=amount, type="transfer_received", wallet_id=receiver_wallet.id))
        
    db.commit()
    return sender_wallet

def get_transactions(db, wallet_id, transaction_type=None):
    query = db.query(models.Transaction).filter(
        models.Transaction.wallet_id == wallet_id
    )

    if transaction_type:
        query = query.filter(models.Transaction.type == transaction_type)

    return query.order_by(models.Transaction.timestamp.desc()).all()