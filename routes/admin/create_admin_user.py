from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.user_models import AdminUserCreateRequest, UserLogin
from utils import hash_password, validate_password, generate_random_token, get_db
from config import logger
from dotenv import load_dotenv
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from passlib.context import CryptContext
load_dotenv("credentials.env")

admin_router = APIRouter(tags=["Admin User Creation"])


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)



# Define the API route
@admin_router.post("/apiv1/create-admin-user/")
async def create_admin_user(user: AdminUserCreateRequest, db: Session = Depends(get_db)):
    
    try:
        
    
        # Check if a user with the provided email exists in UserLogin
        existing_user = db.query(UserLogin).filter(UserLogin.user_email == user.email).first()

        if existing_user:
            return {"message": "Admin user already exists"}
        
        if len(user.fullname) < 3 or len(user.fullname) > 22:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Enter a valid full name length",
                    "method": "POST",
                    "path": "/apiv1/create-admin-user/"
                }
            )
        
        password_validation_response = validate_password(user.password)
        if password_validation_response["status_code"] == 400:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": password_validation_response['message'],
                    "method": "POST",
                    "path": "/apiv1/create-admin-user/"
                }
            )
        
        if password_validation_response["status_code"] == 200:
            hashed_password = hash_password(user.password)
        
            # Create a new user in UserLogin
            new_user_login = UserLogin(
                user_login_id=generate_random_token(),
                user_email=user.email,
                user_fullname=user.fullname,
                user_password=hashed_password,
                user_role='role_4',  
                passwd_status=0
            )

            db.add(new_user_login)
            db.commit()

            return {"message": "Admin user created successfully"}
       

    except HTTPException as e:
        raise e  # Raise the HTTPException with the specific error message
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error creating admin user: {e}",
                "method": "POST",
                "path": "/apiv1/create-admin-user/"
            }
        )