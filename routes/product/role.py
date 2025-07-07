from fastapi import HTTPException, APIRouter, Header, Query , Request, status
import re
from config import logger
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
# from gatewayutils import authenticate_api_key
from models.user_models import Role, RoleDetails, CreateRole, RoleUpdate
from config import  logger
from datetime import datetime, timezone
from typing import List
from utils import get_db
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

router = APIRouter(tags=["Roles"])


# Validation function for role name
def is_valid_role_name(role_name: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9\s]+$', role_name))

@router.post("/apiv1/create-role/")
async def create_role(role: CreateRole, db: Session = Depends(get_db)):
    
    
    if not role.role_name or role.role_name.isspace():
        raise HTTPException(status_code=400, detail={
            "message": "Please enter details. Role name cannot be empty or spaces only.",
            "method": "POST",
            "path": "/apiv1/create-role/"
        })
    
    if not is_valid_role_name(role.role_name):
        raise HTTPException(status_code=400, detail={
            "message": "Role name contains invalid characters. Only alphanumeric characters and spaces are allowed.",
            "method": "POST",
            "path": "/apiv1/create-role/"
        })
    
    try:
        existing_role = db.query(Role).filter(Role.role_name == role.role_name).first()
        if existing_role:
            return {"message": "Role with this name already exists."}
        
        role_count = db.query(func.count(Role.role_id)).scalar()
        role_id = f"role_{role_count + 1}"
        
        db_role = Role(
            role_id=role_id,
            role_name=role.role_name,
            role_status=False,
            role_tstamp=datetime.now(timezone.utc)
        )
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        return {"message": "Role created successfully."}
    
    except Exception as e:
        logger.error(f"An error occurred while creating the role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "POST",
            "path": "/apiv1/create-role/"
        })
    
    finally:
        db.close()


@router.get("/apiv1/get-all-roles/", response_model=List[RoleDetails])
async def get_all_roles(db: Session = Depends(get_db)):
    
    
    try:
        roles = db.query(Role).all()
        return roles
    except Exception as e:
        logger.error(f"An error occurred while fetching roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "GET",
            "path": "/apiv1/get-all-roles/"
        })
    finally:
        db.close()


@router.get("/apiv1/get-specific-roleid/")
async def get_specific_roleid(role_name: str, db: Session = Depends(get_db)):
    
    
    try:
        existing_role = db.query(Role).filter(Role.role_name == role_name).first()
        if existing_role:
            return {"role_id": existing_role.role_id}
        raise HTTPException(status_code=404, detail={
            "message": "Role not found",
            "method": "GET",
            "path": "/apiv1/get-specific-roleid/"
        })

    except Exception as e:
        logger.error(f"An error occurred while fetching roles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "GET",
            "path": "/apiv1/get-specific-roleid/"
        })
    finally:
        db.close()


@router.get("/apiv1/get-active-roles/", response_model=List[RoleDetails])
async def get_active_roles(db: Session = Depends(get_db)):
    
    
    try:
        roles = db.query(Role).filter(Role.role_status != True).all()
        if not roles:
            raise HTTPException(status_code=404, detail={
                "message": "No roles found",
                "method": "GET",
                "path": "/apiv1/get-active-roles/"
            })
        return roles
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "GET",
            "path": "/apiv1/get-active-roles/"
        })


@router.put("/apiv1/update-role-name/")
async def update_role(role_id: str, update_data: RoleUpdate, db: Session = Depends(get_db)):
    
    
    try:
        role = db.query(Role).filter(Role.role_id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail={
                "message": "Role not found",
                "method": "PUT",
                "path": "/apiv1/update-role/"
            })
        
        for key, value in update_data.dict().items():
            if value not in [None, '']:
                if key == "role_name":
                    if not is_valid_role_name(value):
                        raise HTTPException(status_code=400, detail={
                            "message": "Role name contains invalid characters. Only alphanumeric characters and spaces are allowed.",
                            "method": "PUT",
                            "path": "/apiv1/update-role/"
                        })
                setattr(role, key, value)
        
        db.commit()
        db.refresh(role)
        return {"message": "Role updated successfully"}
    
    except Exception as e:
        logger.error(f"An error occurred while updating the role: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "PUT",
            "path": "/apiv1/update-role/"
        })


@router.put("/apiv1/update-role-status/")
async def update_role_status(
    db: Session = Depends(get_db),
    role_id: str = Query(...), 
    status: bool = Query(False)
):
   
    
    try:
        role = db.query(Role).filter(Role.role_id == role_id).first()
        if role is None:
            raise HTTPException(status_code=404, detail={
                "message": "Role not found or has been deleted",
                "method": "PUT",
                "path": "/apiv1/update-role-status/"
            })
        
        # Update the status of the Role
        role.role_status = status
        
        # Commit the changes to the database
        db.commit()
        return {"message": f"Role status updated successfully to {'Inactive' if status else 'Active'}"}
    
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "PUT",
            "path": "/apiv1/update-role-status/"
        })


@router.delete("/apiv1/delete-role")
async def delete_role(role_id: str, db: Session = Depends(get_db)):
   
    
    try:
        role = db.query(Role).filter(Role.role_id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail={
                "message": "Role not found or has been deleted",
                "method": "DELETE",
                "path": "/apiv1/delete-role"
            })
        
        db.delete(role)
        db.commit()
        return {"message": "Role deleted successfully"}
    
    except Exception as e:
        logger.error(f"An error occurred while deleting the role: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail={
            "message": "Internal server error",
            "method": "DELETE",
            "path": "/apiv1/delete-role"
        })
