from sqlalchemy.orm import Session
from app import models, utils
from app import schemas

def create_user_with_wallet(db: Session, user: schemas.UserCreate):
    hashed_pw = utils.hash_password(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.flush()
    new_wallet = models.Wallet(user_id=new_user.id, balance=0.0)
    db.add(new_wallet)
    db.commit()
    db.refresh(new_user)
    return new_user

def deposit_funds(db: Session, wallet_id: int, amount: float):
    with db.begin_nested():
        wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
        wallet.balance += amount
        db.add(models.Transaction(amount=amount, type='deposit', wallet_id=wallet_id))
    db.commit()
    return wallet

def withdraw_funds(db: Session, wallet_id: int, amount: float):
    with db.begin_nested():
        wallet = db.query(models.Wallet).filter(models.Wallet.id == wallet_id).with_for_update().first()
        if wallet.balance < amount:
            raise ValueError('Insufficient funds')
        wallet.balance -= amount
        db.add(models.Transaction(amount=amount, type='withdrawal', wallet_id=wallet_id))
    db.commit()
    return wallet

def transfer_funds(db: Session, sender_wallet_id: int, receiver_email: str, amount: float):
    with db.begin_nested():
        receiver_wallet_info = db.query(models.Wallet).join(models.User).filter(models.User.email == receiver_email).first()
        if not receiver_wallet_info:
            raise ValueError('Receiver not found')
        if sender_wallet_id == receiver_wallet_info.id:
            raise ValueError('You cannot transfer to yourself')
        first_id = min(sender_wallet_id, receiver_wallet_info.id)
        second_id = max(sender_wallet_id, receiver_wallet_info.id)
        db.query(models.Wallet).filter(models.Wallet.id == first_id).with_for_update().first()
        db.query(models.Wallet).filter(models.Wallet.id == second_id).with_for_update().first()
        sender_wallet = db.query(models.Wallet).filter(models.Wallet.id == sender_wallet_id).first()
        receiver_wallet = db.query(models.Wallet).filter(models.Wallet.id == receiver_wallet_info.id).first()
        if sender_wallet.balance < amount:
            raise ValueError('Insufficient funds')
        sender_wallet.balance -= amount
        receiver_wallet.balance += amount
        db.add(models.Transaction(amount=amount, type='transfer_sent', wallet_id=sender_wallet.id))
        db.add(models.Transaction(amount=amount, type='transfer_received', wallet_id=receiver_wallet.id))
    db.commit()
    return sender_wallet

def get_transactions(db: Session, wallet_id: int, transaction_type: str = None):
    query = db.query(models.Transaction).filter(models.Transaction.wallet_id == wallet_id)
    if transaction_type:
        query = query.filter(models.Transaction.type == transaction_type)
    return query.order_by(models.Transaction.timestamp.desc()).all()
