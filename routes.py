from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from database import async_session
from models import UserDB
from schemas import User, UserLogin, ForgotPasswordRequest, ResetPasswordRequest
import base64
import uuid
import smtplib
import os
from email.message import EmailMessage

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

async def send_reset_email(email: str, token: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    if not all([smtp_host, smtp_user, smtp_password]):
        print("SMTP Error: Credentials not fully configured in .env")
        raise HTTPException(status_code=500, detail="Mail server not configured")

    reset_link = f"{frontend_url}/reset-password?token={token}"
    
    msg = EmailMessage()
    msg.set_content(f"Click the link to reset your password: {reset_link}")
    msg["Subject"] = "Password Reset"
    msg["From"] = smtp_from
    msg["To"] = email

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        with server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"SMTP error details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.email == req.email))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")
        
        token = uuid.uuid4().hex
        user.reset_token = token
        await session.commit()
        
        await send_reset_email(user.email, token)
        return {"message": "Reset email sent"}

@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.reset_token == req.token))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        
        encoded_password = base64.b64encode(req.new_password.encode()).decode()
        user.password = encoded_password
        user.reset_token = None
        await session.commit()
        return {"message": "Password reset successfully"}

