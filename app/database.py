import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

#looks for .env file 
load_dotenv()

# grabs the DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")

# stops the app if the URL is missing
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set.")

# Create the connection to database
engine = create_engine(DATABASE_URL)

# Create the SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Create the Base class for models
Base = declarative_base()

#Implementing Atomic Transactions

# used routes to talk to the database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()