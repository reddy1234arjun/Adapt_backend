from fastapi import APIRouter, Depends, HTTPException,Request
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.user_models import UserRegistration,UserLogin,LoginRequest,ForgotPassword, Configuration 
from utils import get_db,hash_password, validate_password,random_token,verify_password
from config import logger,PRIVATE_KEY,PUBLIC_KEY
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from passlib.hash import bcrypt
import re,os,jwt
from sqlalchemy import func
from smtp_mail import send_email
from fastapi_limiter.depends import RateLimiter
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS


router = APIRouter(tags=["user_login"])
load_dotenv("credentials.env")


def contains_html(password):
    # Check if the password contains any HTML tags
    if re.search(r'<.*?>', password):
        return True
    return False

JWT_ALGORITHM = "RS256"
MAX_LOGIN_ATTEMPTS = 5

def create_jwt_token(data: dict, private_key: str):
    return jwt.encode(data, private_key, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str, public_key: str):
    try:
        payload = jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

@router.post("/apiv1/login/")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    # try:
      
       
  
        user = db.query(UserLogin).filter(UserLogin.user_email == data.email).first()
        if not user:
            raise HTTPException(status_code=401, detail={
                "message": "User not found.",
                "method": "POST",
                "path": "/apiv1/login/"
            })
        elif user.status:
            raise HTTPException(status_code=401, detail={
                "message": "Account is locked. Please contact administrator.",
                "method": "POST",
                "path": "/apiv1/login/"
            })

        email = data.email.lower().strip()
        password = data.password.strip()

        # Fetch configuration details
        config = db.query(Configuration).first()
        if not config:
            raise HTTPException(status_code=400, detail={
                "message": "Configuration does not exist.",
                "method": "POST",
                "path": "/apiv1/login/"
            })
        
        # Check if the password is expired according to the 180-day rule
        if config.Days180Flag == 'yes' and user.is_password_expired():
            user.Days180Flag = 1
            db.commit()
            raise HTTPException(status_code=403, detail={
                "message": "Your password has expired. Please change your password.",
                "method": "POST",
                "path": "/apiv1/login/"
            })
        elif config.Days180Flag == 'no':
            user.Days180Flag = -1
            db.commit()

        # Ensure email and password are provided
        if not email or not password:
            raise HTTPException(status_code=401, detail={
                "message": "Enter both email and password.",
                "method": "POST",
                "path": "/apiv1/login/"
            })

        # Handle login attempts lockout logic
        if user.login_attempts >= MAX_LOGIN_ATTEMPTS and user.login_timestamp:
            lockout_end_time = user.login_timestamp + timedelta(minutes=1)
            if lockout_end_time > datetime.utcnow().replace(tzinfo=timezone.utc):
                raise HTTPException(status_code=401, detail={
                    "message": "Account is locked due to multiple unsuccessful login attempts. Please try again later.",
                    "method": "POST",
                    "path": "/apiv1/login/"
                })
            else:
                user.login_attempts = 0
                user.login_timestamp = None
                db.commit()
        
        # Verify the provided password
        if verify_password(password, user.user_password):
            # Check if the user's password is the default password
            if verify_password(password, config.hashedpassword):  # Assuming config.defaultpassword is hashed
                raise HTTPException(status_code=202, detail={
                    "message": "Login successful. Please change your password.",
                    "method": "POST",
                    "path": "/apiv1/login/"
                })
            
            # Successful login with a non-default password
            user.login_attempts = 0
            user.login_timestamp = None
            db.commit()

            token_data = {
                "id": user.user_id,
                "email": user.user_email,
                "exp": datetime.utcnow() + timedelta(hours=1)
            }
            token = create_jwt_token(token_data, PRIVATE_KEY)

            return {"message": "Login successful", "token": token}
        else:
            # Increment login attempts if the password is incorrect
            user.login_attempts += 1
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.login_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)

            db.commit()
            remaining_attempts = MAX_LOGIN_ATTEMPTS - user.login_attempts
            raise HTTPException(status_code=401, detail={
                "message": f"Invalid email or password. Remaining attempts: {remaining_attempts}",
                "method": "POST",
                "path": "/apiv1/login/"
            })

    # except HTTPException as http_exception:
    #     raise http_exception
    # except Exception as e:
    #     logger.error(f"An error occurred: {e}", exc_info=True)
    #     raise HTTPException(status_code=500, detail={
    #         "message": "Internal server error",
    #         "method": "POST",
    #         "path": "/apiv1/login/"
    #     })

@router.post("/apiv1/forgot-password/")
async def forgot_password(data: ForgotPassword, db: Session = Depends(get_db), request: Request = None):
    try:
      
  
        email = data.email.lower()
        if not email:
            raise HTTPException(status_code=401, detail={
                "message": "Enter email.",
                "method": "POST",
                "path": "/apiv1/forgot-password/"
            })
        
        user = db.query(UserLogin).filter(func.lower(UserLogin.user_email) == email).first()
        if not user:
            raise HTTPException(status_code=404, detail={
                "message": "User not found",
                "method": "POST",
                "path": "/apiv1/forgot-password/"
            })
    
        reset_token = random_token()
        client_host = request.client.host
        reset_link = f"http://{client_host}/reset-password?token={reset_token}"   # Construct reset link dynamically
        # send_email(
        #     sender_email=os.getenv("SENDER_EMAIL"), # Sender email
        #     sender_password=os.getenv("SENDER_PASSWORD"),  # Sender password
        #     receiver_mail=email,
        #     subject='Password Reset',
        #     template_file="templates/forgot_password_template1.html",
        #     context={"reset_link": reset_link}
        # )
        
        db.commit()
        
        return {"message": "Password reset link sent successfully to your registered email address."}
    
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        logger.error(f"Error sending reset link: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Error sending reset link.",
            "method": "POST",
            "path": "/apiv1/forgot-password/"
        })

@router.put("/apiv1/reset-password/")
async def reset_password(email: str, new_password: str, confirm_new_password: str, db: Session = Depends(get_db)):
    try:
        
  
        email = email.lower()
    
        if not new_password.strip() or not confirm_new_password.strip():
            raise HTTPException(status_code=400, detail={
                "message": "Password is required",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })
        
        if ' ' in new_password.strip():
            raise HTTPException(status_code=400, detail={
                "message": "Password cannot contain spaces.",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })

        if not new_password or not confirm_new_password:
            raise HTTPException(status_code=400, detail={
                "message": "Invalid input data",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })
        
        new_password = new_password.strip()
        confirm_new_password = confirm_new_password.strip()
        
        user = db.query(UserLogin).filter_by(user_email=email).first()
        if not user:
            raise HTTPException(status_code=404, detail={
                "message": "Invalid user",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })

        if new_password != confirm_new_password:
            raise HTTPException(status_code=400, detail={
                "message": "Passwords do not match",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })
    
        if contains_html(new_password) or contains_html(confirm_new_password):
            raise HTTPException(status_code=400, detail={
                "message": "Password is not secure.",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })
        
        hashed_password_from_db = user.user_password 

        if bcrypt.verify(new_password, hashed_password_from_db):
            raise HTTPException(status_code=400, detail={
                "message": "Please choose a different password. You cannot reuse your current password.",
                "method": "PUT",
                "path": "/apiv1/reset-password/"
            })

        user.user_password = hash_password(new_password)
        db.commit()
        return {"message": "Password reset successfully"}
    
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        logger.error(f"An error occurred while resetting the password: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error.",
            "method": "PUT",
            "path": "/apiv1/reset-password/"
        })

    
@router.delete("/apiv1/user-delete/{user_login_id}")
async def delete_user_login(user_login_id: str, db: Session = Depends(get_db)):
    try:
    
  
        user_login = db.query(UserLogin).filter(UserLogin.user_login_id == user_login_id).first()

        if not user_login:
            raise HTTPException(status_code=404, detail="User login not found")

        user_login.status = True
        db.commit()
        return {"message": f"User deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete user login")