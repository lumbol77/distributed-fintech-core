from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import ConfigDict

class UserCreate(BaseModel):
    email: EmailStr
    password: str
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
class UserLogin(BaseModel):
    email: EmailStr
    password: str
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

#Create a Deposit schema

class DepositRequest(BaseModel):
    amount: float

#let's build the Withdraw Money feature

class WithdrawRequest(BaseModel):
    amount: float

#Let’s build transaction history

class TransactionResponse(BaseModel):
    id: int
    amount: float
    type: str
    timestamp: datetime
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

 #The above code allows Pydantic to return transaction objects.
#Let’s build transfers next
#User A sends money to User B
# Amount is removed from sender wallet
# Amount is added to receiver wallet
# Two transactions are recorded:
# debit (sender)
# credit (receiver)
class TransferRequest(BaseModel):
         receiver_email: EmailStr
         amount: float
# Add Transfer History schema
class TransferHistoryResponse(BaseModel):
    id: int
    amount: float
    type: str
    timestamp: datetime
    class Config:
        from_attributes = True