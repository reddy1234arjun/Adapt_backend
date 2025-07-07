from fastapi import APIRouter, Depends, HTTPException,UploadFile, File
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.user_models import UserLogin,UserProfileCreate,UserProfile
from utils import generate_random_token, get_db
import os
from config import logger
from dotenv import load_dotenv
from uuid import uuid4
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS

router = APIRouter(tags=["user_profile"])

load_dotenv("credentials.env")

@router.post("/apiv1/create-user-profile-address/")
async def create_user_profile(user_login_id: str, user_profile: UserProfileCreate, db: Session = Depends(get_db)):
    try:
        

        # Check if the UserLogin with the given user_login_id exists
        user_login = db.query(UserLogin).filter(UserLogin.user_login_id == user_login_id).first()
        if not user_login:
            raise HTTPException(status_code=404, detail="User login not found")

        # Convert user_address and delivery_address to dictionary
        user_address_dict = user_profile.user_address.dict()
        delivery_address_dict = user_profile.delivery_address.dict()

        # Create UserProfile instance with the provided details
        new_user_profile = UserProfile(
            user_profile_id=generate_random_token(),
            user_login_id=user_login_id,
            user_address=user_address_dict,
            delivery_address=delivery_address_dict
        )

        # Add the new UserProfile instance to the database session
        db.add(new_user_profile)
        # Commit the transaction to persist the changes to the database
        db.commit()

        return {"message": "User profile created successfully", "user_profile_id": new_user_profile.user_profile_id}

    except HTTPException as http_exception:
        # Wrap HTTPException with additional detail
        raise HTTPException(status_code=http_exception.status_code, detail={
            "message": http_exception.detail,
            "method": "POST",
            "path": "/apiv1/create-user-profile-address/"
        })
    except Exception as e:
        # Rollback the transaction in case of any error
        db.rollback()
        logger.error(f"Error Creating User Profile: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(status_code=500, detail={
            "message": f"Internal server error.{e}",
            "method": "POST",
            "path": "/apiv1/create-user-profile-address/"
        })


UPLOAD_FOLDER = 'profile_images/'

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@router.post("/apiv1/upload-profile-image/")
async def upload_profile_image(user_profile_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        
        # Check if the UserProfile with the given user_profile_id exists
        user_profile = db.query(UserProfile).filter(UserProfile.user_profile_id == user_profile_id).first()
        if not user_profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Save the uploaded file to the designated folder
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

        # Write the file to the designated path
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Update the user profile with the image path
        user_profile.user_profile_img = file_path
        db.commit()

        return {"message": "Profile image uploaded successfully", "file_path": file_path}

    except Exception as e:
        db.rollback()
        logger.error(f"Error Uploading Profile Image: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(status_code=500, detail={
            "message": f"Internal server error.{e}",
            "method": "POST",
            "path": "/apiv1/upload-profile-image/"
        })

@router.get("/apiv1/get-user_profile/{user_profile_id}")
async def get_user_profile(user_profile_id: str, db: Session = Depends(get_db)):
    try:
        
        profile = db.query(UserProfile).filter(UserProfile.user_profile_id == user_profile_id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="UserProfile not found")
        return profile

    except Exception as e:
        logger.error(f"Error Getting User Profile: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise HTTPException(status_code=500, detail={
            "message": f"Internal server error.{e}",
            "method": "GET",
            "path": f"/apiv1/get-user_profile/{user_profile_id}"
        })
