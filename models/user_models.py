from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Sequence, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.event import listens_for
from sqlalchemy import func
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import JSONB 


Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Configuration(Base):
    __tablename__ = 'configuration'
    confid = Column(Integer, primary_key=True, autoincrement=True, unique=True)  # Auto-incrementing integer ID
    supportemail = Column(String, nullable=False)
    defaultpassword = Column(String, nullable=False)
    hashedpassword = Column(String, nullable=False)
    logo = Column(String, nullable=True)
    Days180Flag = Column(String, default="False")
    status = Column(Boolean, default=False)
    tstamp = Column(DateTime(timezone=True), server_default=func.now())

class ConfigurationCreate(BaseModel):
    defaultpassword:str
    supportemail: EmailStr
    Days180Flag: Optional[str]='yes'
    logo: str
   

class UserRegistration(Base):
    __tablename__ = "user_registration"

    user_id = Column(String, primary_key=True, unique=True, index=True)
    user_firstname = Column(String, nullable=False)
    user_lastname = Column(String, nullable=False)
    user_email = Column(String, unique=True, index=True, nullable=False)
    user_password = Column(String, nullable=False)
    user_token = Column(String, nullable=False)
    user_email_flag = Column(Boolean, default=False)
    status = Column(Boolean, default=False)
    tstamp = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

    logins = relationship("UserLogin", back_populates="user")

class UserLogin(Base):
    __tablename__ = "user_login"
    user_login_id = Column(String, primary_key=True, unique=True, index=True)
    user_id = Column(String, ForeignKey('user_registration.user_id'))
    user_fullname=Column(String)
    user_email = Column(String, unique=True, index=True, nullable=False)
    user_password = Column(String, nullable=False)
    user_role=Column(String, nullable=False)
    passwd_status=Column(Integer)
    login_attempts = Column(Integer, default=0)
    login_timestamp = Column(DateTime(timezone=True))
    Days180Flag = Column(Integer,default=1)
    status = Column(Boolean, default=False)
    tstamp = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    
    # Define relationship
    user = relationship("UserRegistration", back_populates="logins")
    profiles = relationship("UserProfile", back_populates="login")
    def is_password_expired(self):
        if self.tstamp:
            current_time = datetime.now(timezone.utc)
            delta = current_time - self.tstamp
            return delta.days > 180
        return False

class AddUser(BaseModel):
    user_fullname: str
    user_email: EmailStr
    user_role: str


class UserProfile(Base):
    __tablename__ = "user_profile"
    user_profile_id = Column(String, primary_key=True, unique=True, index=True)
    user_login_id = Column(String, ForeignKey('user_login.user_login_id'))
    user_profile_img = Column(String)
    user_address = Column(JSONB)  
    delivery_address=Column(JSONB) 
    status = Column(Boolean, default=False)
    tstamp = Column(DateTime(timezone=True), nullable=True, server_default=func.now())
    login = relationship("UserLogin", back_populates="profiles")

    
# Pydantic model for request body

class UserCreate(BaseModel):
    user_firstname: str
    user_lastname: str
    user_email: EmailStr
    user_password: str

class UserResponse(BaseModel):
    user_id: str
    user_fullname: str
    user_email:str
    user_email: EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPassword(BaseModel):
    email: EmailStr

class Address(BaseModel):
    address: str
    state: str
    country: str
    phone_number: str
    pincode: str

class UserProfileCreate(BaseModel):
    user_address: Address
    delivery_address: Address

class UserUpdate(BaseModel):
    user_fullname: str
   


class Role(Base):
    __tablename__ = 'roles'
    role_id = Column(String, primary_key=True, unique=True)
    role_name =  Column(String)    
    role_status = Column(Boolean, default=False)
    role_tstamp = Column(DateTime(timezone=True), nullable=True, server_default=func.now())

class CreateRole(BaseModel):
    role_name: str


class RoleDetails(BaseModel):
    role_id : str
    role_name :  str
    role_status : bool


class RoleUpdate(BaseModel):
    role_name: Optional[str]



class AdminUserCreateRequest(BaseModel):
    email: str
    fullname: str
    password: str    