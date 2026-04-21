from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
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