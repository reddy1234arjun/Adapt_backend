from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import HTTPException
from utils import get_db
from models.user_models import ConfigurationCreate,Configuration
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
router = APIRouter(tags=["internal_details"])
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password: str):
    return pwd_context.hash(password)

@router.post("/apiv1/configurations-create/")
async def create_configuration(config: ConfigurationCreate, db: Session = Depends(get_db)):
    try:
       
        default_password = config.defaultpassword
        hashed_password = get_password_hash(default_password)
        db_config = Configuration(
            supportemail=config.supportemail,
            defaultpassword=config.defaultpassword,
            Days180Flag=config.Days180Flag,
            hashedpassword=hashed_password,
            logo=config.logo
        )
        
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        db.close()
        return {
            "message": "Configuration created successfully",
            "supportemail": db_config.supportemail,
            "Days180Flag": db_config.Days180Flag,
            "defaultpassword": db_config.defaultpassword,
            "logo": db_config.logo,
            "status": db_config.status
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}", headers={"method": "POST", "path": "/apiv1/configurations-create/"})


@router.put("/apiv1/update-configurations/{config_id}")
async def update_configuration(config_id: int, config: ConfigurationCreate, db: Session = Depends(get_db)):
    
    db_config = db.query(Configuration).filter(Configuration.confid == config_id).first()
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration not found", headers={"method": "PUT", "path": f"/apiv1/update-configurations/{config_id}"})
    
    try:
        if config.supportemail and config.supportemail.strip():
            db_config.supportemail = config.supportemail
        if config.Days180Flag and config.Days180Flag.strip():
            db_config.Days180Flag = config.Days180Flag
        if config.defaultpassword and config.defaultpassword.strip():
            db_config.defaultpassword = config.defaultpassword
        if config.logo and config.logo.strip():
            db_config.logo = config.logo

        db.commit()
        db.refresh(db_config)

        return {
            "message": "Configuration updated successfully",
            "supportemail": db_config.supportemail,
            "Days180Flag": db_config.Days180Flag,
            "logo": db_config.logo,
            "status": db_config.status
        }
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}", headers={"method": "PUT", "path": f"/apiv1/update-configurations/{config_id}"})


@router.get("/apiv1/get-configurations/{config_id}")
async def get_configuration(config_id: int, db: Session = Depends(get_db)):
    try:
        
        db_config = db.query(Configuration).filter(Configuration.confid == config_id).first()
        if not db_config:
            raise HTTPException(status_code=404, detail="Configuration not found", headers={"method": "GET", "path": f"/apiv1/get-configurations/{config_id}"})

        return {
            "supportemail": db_config.supportemail,
            "Days180Flag": db_config.Days180Flag,
            "logo": db_config.logo,
            "status": db_config.status,
            "defaultpassword": db_config.defaultpassword,
            "tstamp": db_config.tstamp
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving configuration: {str(e)}", headers={"method": "GET", "path": f"/apiv1/get-configurations/{config_id}"})
