from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)



class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)  # from Auth Service
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer)
    language = Column(String, default="Unknown")
    pages = Column(Integer, nullable=False)
    pages_read = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    comments = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)