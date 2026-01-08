from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update
from database import async_session
from models import UserDB
from schemas import User, UserLogin, ForgotPasswordRequest, ResetPasswordRequest, ResendVerificationRequest
import base64
import uuid
import smtplib
import os
from email.message import EmailMessage

router = APIRouter()

async def send_auth_email(email: str, subject: str, body: str):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM")

    if not all([smtp_host, smtp_user, smtp_password]):
        print(f"SMTP Error: Credentials not fully configured in .env for {subject}")
        raise HTTPException(status_code=500, detail="Mail server not configured")

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
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
        verification_token = uuid.uuid4().hex
        new_user = UserDB(
            firstName=user.firstName,
            lastName=user.lastName,
            email=user.email,
            studentId=user.studentId,
            password=encoded_password,
            is_verified=0,
            verification_token=verification_token
        )
        session.add(new_user)
        await session.commit()
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verify_link = f"{frontend_url}/verify-email?token={verification_token}"
        await send_auth_email(
            user.email, 
            "Verify Your Email", 
            f"Click the link to verify your email address: {verify_link}"
        )
        
        return {"message": "User registered successfully. Please check your email to verify your account."}

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
            if not user.is_verified:
                raise HTTPException(
                    status_code=403, 
                    detail={"message": "Email not verified", "email": user.email}
                )
                
            return {
                "message": "Login successful",
                "user": {
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "studentId": user.studentId
                }
            }
        
    raise HTTPException(status_code=401, detail="Invalid student ID or password")

@router.get("/verify-email")
async def verify_email(token: str):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.verification_token == token))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        user.is_verified = 1
        user.verification_token = None
        await session.commit()
        return {"message": "Email verified successfully"}

@router.post("/resend-verification")
async def resend_verification(req: ResendVerificationRequest):
    async with async_session() as session:
        result = await session.execute(select(UserDB).where(UserDB.email == req.email))
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(status_code=404, detail="Email not found")
        
        if user.is_verified:
            return {"message": "Email is already verified"}
        
        token = uuid.uuid4().hex
        user.verification_token = token
        await session.commit()
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        verify_link = f"{frontend_url}/verify-email?token={token}"
        await send_auth_email(
            user.email, 
            "Verify Your Email", 
            f"Click the link to verify your email address: {verify_link}"
        )
        return {"message": "Verification email resent"}

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
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_link = f"{frontend_url}/reset-password?token={token}"
        await send_auth_email(user.email, "Password Reset", f"Click the link to reset your password: {reset_link}")
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

