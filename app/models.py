from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime,Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("Wallet", back_populates="owner", uselist=False)


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    balance = Column(Float, default=0.0)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="wallet")
    transactions = relationship("Transaction", back_populates="wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    type = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    wallet_id = Column(Integer, ForeignKey("wallets.id"))

    wallet = relationship("Wallet", back_populates="transactions")

__table_args__ = (
        # accelerate querying a specific wallet transactional ledger history
        Index("ix_transactons_wallet_id", "wallet_id"),
        
        # FIXED: Changed "wallet" to "wallet_id"
        # composite index to rapidly sort transactional data fields by time
        Index("ix_transctions_wallet_timestamp", "wallet_id", "timestamp"),
    )