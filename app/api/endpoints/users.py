from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, utils
from app.database import get_db
from app import schemas
from app.security import create_access_token
from app.schemas import UserCreate, UserResponse, UserLogin, Token
from app.crud import wallet_crud as crud 
router = APIRouter(tags=["Users"])
@router.post("/", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Check if user exists
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Call CRUD to handle the actual creation
    # We move the "Create User + Create Wallet" logic to crud/wallet_crud.py
    # This keeps this route "Thin" and clean.
    new_user = crud.create_user_with_wallet(db, user)
    
    return new_user
@router.post("/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # verify_password remains in utils (which is correct)
    if not utils.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    access_token = create_access_token({"sub": user.email})

    return {"access_token": access_token, "token_type": "bearer"}