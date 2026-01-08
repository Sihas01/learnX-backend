from pydantic import BaseModel

class User(BaseModel):
    firstName: str
    lastName: str
    email: str
    studentId: str
    password: str

class UserLogin(BaseModel):
    studentId: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ResendVerificationRequest(BaseModel):
    email: str
