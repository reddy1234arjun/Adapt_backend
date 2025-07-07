from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.product_models import StoreSettings, StoreSettingsCreate, StoreSettingsUpdate
from utils import get_db
from config import logger 
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
router = APIRouter(tags=["store"])
import re

def validate_string_field(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")
    trimmed_value = value.strip()
    if not trimmed_value:
        raise ValueError(f"{field_name} cannot be empty or whitespace.")
    if not re.match(r'^[A-Za-z\s]+$', trimmed_value):
        raise ValueError(f"{field_name} must contain only characters.")
    return trimmed_value

def validate_postcode(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Postcode must be a string.")
    trimmed_value = value.strip()
    if not trimmed_value:
        raise ValueError("Postcode cannot be empty or whitespace.")
    if not re.match(r'^\d+$', trimmed_value):
        raise ValueError("Postcode must contain only numbers.")
    return trimmed_value
def trim_string(value: str) -> str:
    return value.strip() if isinstance(value, str) else value

@router.post("/apiv1/create-store-settings/")
async def create_store_settings(store: StoreSettingsCreate, db: Session = Depends(get_db)):
    try:
       

        # Validate and trim fields
        store.addressline1 = trim_string(store.addressline1)
        store.addressline2 = trim_string(store.addressline2) if store.addressline2 else None
        store.country = validate_string_field(trim_string(store.country), "Country")
        store.state = validate_string_field(trim_string(store.state), "State")
        store.city = validate_string_field(trim_string(store.city), "City")
        store.postcode = validate_postcode(trim_string(store.postcode))  # Validate postcode
        store.currency = trim_string(store.currency)
        store.currencypostion = trim_string(store.currencypostion)

        store_count = db.query(func.count(StoreSettings.storeid)).scalar()
        storeid = f"store_{store_count + 1}"
        db_store_settings = StoreSettings(
            storeid=storeid,
            addressline1=store.addressline1,
            addressline2=store.addressline2,
            country=store.country,
            state=store.state,
            city=store.city,
            postcode=store.postcode,
            currency=store.currency,
            currencypostion=store.currencypostion,
            status=store.status
        )
        db.add(db_store_settings)
        db.commit()
        db.refresh(db_store_settings)

        return {
            "message": "Store settings created successfully",
            "store_settings": db_store_settings
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={
            "message": str(ve),
            "method": "POST",
            "path": "/apiv1/create-store-settings/"
        })
    except Exception as e:
        logger.error(f"Error creating store settings: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Error creating store settings",
            "method": "POST",
            "path": "/apiv1/create-store-settings/"
        })


@router.get("/apiv1/get-store-settings/{storeid}")
async def get_store_settings(storeid: str, db: Session = Depends(get_db)):
    try:
        
        store_settings = db.query(StoreSettings).filter(StoreSettings.storeid == storeid).first()
        if not store_settings:
            raise HTTPException(status_code=404, detail={
                "message": "Store settings not found",
                "method": "GET",
                "path": f"/apiv1/get-store-settings/{storeid}"
            })

        return store_settings
    except Exception as e:
        logger.error(f"Error fetching store settings: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Error fetching store settings",
            "method": "GET",
            "path": f"/apiv1/get-store-settings/{storeid}"
        })


@router.get("/apiv1/get-all-store-settings/")
async def get_all_store_settings(db: Session = Depends(get_db)):
    try:
        
        store_settings_list = db.query(StoreSettings).all()

        if not store_settings_list:
            raise HTTPException(status_code=404, detail={
                "message": "No store settings found",
                "method": "GET",
                "path": "/apiv1/get-all-store-settings/"
            })

        return store_settings_list
    except Exception as e:
        logger.error(f"Error fetching all store settings: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Error fetching store settings",
            "method": "GET",
            "path": "/apiv1/get-all-store-settings/"
        })


@router.put("/apiv1/update-store-settings/{storeid}")
async def update_store_settings(storeid: str, store_update: StoreSettingsUpdate, db: Session = Depends(get_db)):
    try:
        
        store_settings = db.query(StoreSettings).filter(StoreSettings.storeid == storeid).first()

        if not store_settings:
            raise HTTPException(status_code=404, detail={
                "message": "Store settings not found",
                "method": "PUT",
                "path": f"/apiv1/update-store-settings/{storeid}"
            })

        # Update the fields if provided in the request and are not None or empty
        for key, value in store_update.dict(exclude_unset=True).items():
            if value is not None and value != "":
                setattr(store_settings, key, value)

        db.commit()
        db.refresh(store_settings)

        return {
            "message": "Store settings updated successfully",
            "store_settings": store_settings
        }
    except Exception as e:
        logger.error(f"Error updating store settings: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": "Error updating store settings",
            "method": "PUT",
            "path": f"/apiv1/update-store-settings/{storeid}"
        })