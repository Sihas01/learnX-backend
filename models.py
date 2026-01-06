from sqlalchemy import Column, Integer, String
from database import Base

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstName = Column(String(100))
    lastName = Column(String(100))
    email = Column(String(255), unique=True)
    studentId = Column(String(50), unique=True)
    password = Column(String(255))
    reset_token = Column(String(255), nullable=True)
