from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import EmailStr
from fastapi import HTTPException
from models.user_models import AddUser, AdminUserCreateRequest, Configuration, UserRegistration,UserCreate,UserResponse,UserLogin, UserUpdate
from utils import hash_password, validate_password, generate_random_token, get_db,random_token
from smtp_mail import send_email
import os
from config import logger
from dotenv import load_dotenv
import re
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from passlib.context import CryptContext
load_dotenv("credentials.env")

router = APIRouter(tags=["user_registation"])
# Password hashing utility
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)
    
def copy_data(db: Session, email: str):
    try:
        # Check if a user with the provided email exists in UserRegistration
        existing_user = db.query(UserRegistration).filter(UserRegistration.user_email == email).first()
        username=f'{existing_user.user_firstname} {existing_user.user_lastname}'
        
        # Check if the user exists
        if existing_user:
            # Create a new user in UserLogin
            new_user_login = UserLogin(
                user_login_id=generate_random_token(),
                user_email=existing_user.user_email,
                user_fullname=username,
                user_password=existing_user.user_password,
                user_role='role_4',
                passwd_status=0
            )
            db.add(new_user_login)
        
            # Commit the changes
            db.commit()
            return {"message": "Data copied successfully"}
        else:
            return {"message": "User not found with the provided email"}
    except Exception as e:
        # Handle any exceptions or errors that may occur during this process
        db.rollback()
        print(f"Error copying data: {str(e)}")
        raise e
    

# Function to check if password contains HTML code
def contains_html(password):
    if re.search(r'<.*?>', password):
        return True
    return False
email_pattern = r"^[A-Za-z.]+$"
name_pattern = r"^[A-Za-z].*"

letter_pattern = re.compile(r"^[a-zA-Z]")

def validate_email(email):
    # Remove spaces from the middle of the email address
    email = re.sub(r'\s+', '', email)
    # Check if email is empty after removing spaces
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    return email
@router.post("/apiv1/user-registration/")
async def user_registration(data: UserCreate, db: Session = Depends(get_db)):
    try:
        
  
        # Normalize and validate email
        data.user_email = (data.user_email.lower()).strip()
        firstname = data.user_firstname.strip()
        lastname = data.user_lastname.strip()
        
        # Validate user name
        if not letter_pattern.match(data.user_firstname) and not letter_pattern.match(data.user_lastname):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "First and last name must start with a letter",
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        if len(firstname) < 3 or len(firstname) > 16:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Enter a valid first name length",
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        if len(lastname) < 3 or len(lastname) > 16:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Enter a valid last name length",
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        if firstname == lastname:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "First name and last name cannot be the same",
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        
        user = db.query(UserRegistration).filter(UserRegistration.user_email == data.user_email).first()
        if user:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "User with this email already exists.",
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        
        # Validate the password
        password_validation_response = validate_password(data.user_password)
        if password_validation_response["status_code"] == 400:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": password_validation_response['message'],
                    "method": "POST",
                    "path": "/apiv1/user-registration/"
                }
            )
        
        if password_validation_response["status_code"] == 200:
            hashed_password = hash_password(data.user_password)
            user_id = generate_random_token()
            token = random_token()
            
            # Proceed with user registration logic
            user_data = {
                'user_id': user_id,
                'user_firstname': data.user_firstname,
                'user_lastname': data.user_lastname,
                'user_email': data.user_email,
                'user_password': hashed_password, 
                'user_token': token
            }
            new_user = UserRegistration(**user_data)
            db.add(new_user)
            db.commit()
            
            # # Send welcome email
            # send_email(
            #     sender_email=os.getenv("SENDER_EMAIL"),
            #     sender_password=os.getenv("SENDER_PASSWORD"),
            #     receiver_mail=data.user_email,
            #     subject='Welcome to User Management',
            #     template_file="templates/onboarding_template.html",
            #     context={"Email_Address": data.user_email, "username": data.user_firstname, "token": token}
            # )
            return {"message": "User registration successful", "user": user_data}
    except HTTPException as e:
        raise e  # Raise the HTTPException with the specific error message
    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error registering user: {e}",
                "method": "POST",
                "path": "/apiv1/user-registration/"
            }
        )

@router.put("/apiv1/update-email-flag/")
async def update_email_flag(email: str, db: Session = Depends(get_db)):
    try:
        
  
        user = db.query(UserRegistration).filter(UserRegistration.user_email == email).first()
        if user is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "method": "PUT",
                    "path": "/apiv1/update-email-flag/"
                }
            )
        
        user.user_email_flag = True
        
        db.commit()
        copy_data(db, user.user_email)
        return {"message": "User email flag status successfully"}
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        logger.error(f"Error Updating Email Flag status: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error updating email flag status",
                "method": "PUT",
                "path": "/apiv1/update-email-flag/"
            }
        )

@router.put("/apiv1/resend-email-token/")
async def resend_email_token(emailaddress: str, db: Session = Depends(get_db)):
    try:
        
  
        user = db.query(UserRegistration).filter(UserRegistration.user_email == emailaddress).first()
        if not user:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "User not found",
                    "method": "PUT",
                    "path": "/apiv1/resend-email-token/"
                }
            )

        if user.user_email_flag == 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Email already verified. Please login.",
                    "method": "PUT",
                    "path": "/apiv1/resend-email-token/"
                }
            )
        
        new_email_token = generate_random_token()

        # Send welcome email
        # send_email(
        #     sender_email=os.getenv("SENDER_EMAIL"),
        #     sender_password=os.getenv("SENDER_PASSWORD"),
        #     receiver_mail=user.user_email,
        #     subject='Welcome to User Management',
        #     template_file="templates/onboarding_template.html",
        #     context={"Email_Address": user.user_email, "username": user.user_firstname, "token": new_email_token}
        # )
        
        # Update the email token in the database
        user.user_token = new_email_token
        db.commit()    
        return {"message": "Email token resent successfully"}
    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        logger.error(f"Error Resending Mail Token: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error resending mail token",
                "method": "PUT",
                "path": "/apiv1/resend-email-token/"
            }
        )



@router.post("/apiv1/add-user/")
def create_user_login(user: AddUser, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        existing_user = db.query(UserLogin).filter(UserLogin.user_email == user.user_email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate a random UUID for the user_login_id
        user_login_id = generate_random_token()
        configration = db.query(Configuration).first()
        default_password = configration.defaultpassword
        hashed_password = get_password_hash(default_password)
        
        # Create a new user object
        new_user = UserLogin(
            user_login_id=user_login_id,
            user_fullname=user.user_fullname,
            user_email=user.user_email,
            user_password=hashed_password,
            user_role=user.user_role,
            passwd_status=-1  # Set initial password status as -1 (e.g., needs to change password)
        )
        send_email(
                sender_email=os.getenv("SENDER_EMAIL"),
                sender_password=os.getenv("SENDER_PASSWORD"),
                receiver_mail=user.user_email,
                subject='Welcome to User Management',
                template_file="templates/adduser_template.html",
                context={"username": user.user_fullname, "Default_Password": default_password}
            )
        
        # Add to DB and commit
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {"message": "User created successfully", "user_login_id": new_user.user_login_id}

    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Error creating user login: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error creating user",
                "method": "POST",
                "path": "/apiv1/add-user/"
            }
        )

@router.put("/apiv1/update-user-registration/{user_id}")
async def update_user_registration(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    try:
        

        # Check if the UserRegistration with the given user_id exists
        user = db.query(UserLogin).filter(UserLogin.user_login_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail={
                "message": "User not found",
                "method": "PUT",
                "path": f"/apiv1/update-user-registration/{user_id}"
            })

        # Update the first name and last name
        if user_update.user_fullname:
            user.user_fullname = user_update.user_fullname

        db.commit()

        return {"message": "User registration updated successfully"}
    
    except HTTPException as http_exception:
        raise http_exception
    
    except Exception as e:
        logger.error(f"Error Updating User Registration: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error updating user registration",
                "method": "PUT",
                "path": f"/apiv1/update-user-registration/{user_id}"
            }
        )


@router.get("/apiv1/user-details/{user_login_id}", response_model=UserResponse)
async def get_user(user_login_id: str, db: Session = Depends(get_db)):
    try:
        

        user = db.query(UserLogin).filter(UserLogin.user_login_id == user_login_id).first()
        if user is None:
            raise HTTPException(status_code=404, detail={
                "message": "User not found",
                "method": "GET",
                "path": f"/apiv1/user-details/{user_login_id}"
            })

        return user
    
    except HTTPException as http_exception:
        raise http_exception
    
    except Exception as e:
        logger.error(f"Error Getting User: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error getting user",
                "method": "GET",
                "path": f"/apiv1/user-details/{user_login_id}"
            }
        )





