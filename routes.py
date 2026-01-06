from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from database import async_session
from models import UserDB
from schemas import User, UserLogin
import base64

router = APIRouter()

@router.post("/register")
async def register(user: User):
    async with async_session() as session:
        result = await session.execute(
            select(UserDB).where(
                (UserDB.studentId == user.studentId) | (UserDB.email == user.email)
            )
        )
        existing_user = result.scalars().first()
        if existing_user:
            if existing_user.studentId == user.studentId:
                raise HTTPException(status_code=400, detail="Student ID already registered")
            else:
                raise HTTPException(status_code=400, detail="Email already registered")
        
        encoded_password = base64.b64encode(user.password.encode()).decode()
        new_user = UserDB(
            firstName=user.firstName,
            lastName=user.lastName,
            email=user.email,
            studentId=user.studentId,
            password=encoded_password
        )
        session.add(new_user)
        await session.commit()
        return {"message": "User registered successfully"}

@router.post("/login")
async def login(user_login: UserLogin):
    async with async_session() as session:
        encoded_password = base64.b64encode(user_login.password.encode()).decode()
        result = await session.execute(
            select(UserDB).where(
                UserDB.studentId == user_login.studentId,
                UserDB.password == encoded_password
            )
        )
        user = result.scalars().first()
        
        if user:
            return {
                "message": "Login successful",
                "user": {
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "studentId": user.studentId
                }
            }
        
    raise HTTPException(status_code=401, detail="Invalid student ID or password")

