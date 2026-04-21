import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from dotenv import load_dotenv

load_dotenv()

# CONFIGURATION

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

security = HTTPBearer()

# CREATE ACCESS TOKEN

def create_access_token(data: dict, expires_delta: int = None):
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# VERIFY TOKEN
 
def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        return email

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# RETRIEVE CURRENT USER FROM TOKEN

def get_current_user(
    credentials=Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials
    email = verify_access_token(token)

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user