from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from utils import get_db
from fastapi_limiter.depends import RateLimiter
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from models.user_models import UserRegistration
from sqlalchemy import func

router = APIRouter(tags=["user_details"])

@router.get("/apiv1/user-stats/")
async def get_user_stats(db: Session = Depends(get_db)):
    try:
        total_users = db.query(func.count(UserRegistration.user_id)).scalar()
        verified_users = db.query(func.count(UserRegistration.user_id)).filter(UserRegistration.user_email_flag == True).scalar()

        return {
            "total_register_users": total_users,
            "verified_users": verified_users
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}", headers={"method": "GET", "path": "/apiv1/user-stats/"})


@router.get("/apiv1/total-users-stats/")
async def get_user_stats(db: Session = Depends(get_db)):
    try:
        # Query to get total users with their details
        total_users = db.query(
            UserRegistration.user_id,
            UserRegistration.user_email,
            UserRegistration.user_firstname,
            UserRegistration.user_lastname
        ).all()

        # Query to get verified users with their details
        verified_users = db.query(
            UserRegistration.user_id,
            UserRegistration.user_email,
            UserRegistration.user_firstname,
            UserRegistration.user_lastname
        ).filter(UserRegistration.user_email_flag == True).all()

        total_users_count = len(total_users)
        verified_users_count = len(verified_users)

        total_users_list = [
            {
                "user_id": user.user_id,
                "user_email": user.user_email,
                "user_firstname": user.user_firstname,
                "user_lastname": user.user_lastname
            }
            for user in total_users
        ]

        verified_users_list = [
            {
                "user_id": user.user_id,
                "user_email": user.user_email,
                "user_firstname": user.user_firstname,
                "user_lastname": user.user_lastname
            }
            for user in verified_users
        ]

        return {
            "total_register_users_count": total_users_count,
            "total_register_users": total_users_list,
            "verified_users_count": verified_users_count,
            "verified_users": verified_users_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}", headers={"method": "GET", "path": "/apiv1/total-users-stats/"})
