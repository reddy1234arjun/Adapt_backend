
import csv
from datetime import datetime
import io
import os
import re
from uuid import uuid4
import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import EmailStr
from fastapi import HTTPException
from models.product_models import ProductCategory,ProductCategoryCreate,ProductCategoryUpdate, ProductSubCategory, ProductionTable, StatusUpdate 
from models.product_models import ProductCategory 
from utils import get_db
from config import logger 
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from typing import List, Optional
from models.user_models import Configuration
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError


router = APIRouter(tags=["product_cat"])


def validate_name(input_name: str, field_name: str) -> str:
    cleaned_name = input_name.strip()
    if not re.match(r'^[A-Za-z0-9\s!@#$%^&*(),.?":{}|<>_-]+$', cleaned_name):
        raise HTTPException(status_code=400, detail=f"{field_name} should contain only letters, digits and special characters.")
    return cleaned_name

UPLOAD_CATEGORY_FOLDER = "uploads/categories"  # Define the upload root folder

@router.post("/apiv1/create-product-categories/")
async def create_product_category(
    name: Optional[str] = Form(None),  
    description: Optional[str] = Form(None),  
    status: Optional[bool] = Form(False), 
    parent: Optional[str] = Form(None),  
    file: UploadFile = File(None), 
    db: Session = Depends(get_db)
):
    try:
       
        # Validate and clean up the names
        cleaned_category_name = validate_name(name, "Category name").title() if name else None
        cleaned_parent_name = validate_name(parent, "Parent name").title() if parent else None

        # Handle image upload and store the image path
        image_path = None
        if file:
            # Create a folder for the category or subcategory if it doesn't exist
            category_folder = os.path.join(UPLOAD_CATEGORY_FOLDER, cleaned_category_name or cleaned_parent_name)
            if not os.path.exists(category_folder):
                os.makedirs(category_folder)

            # Generate unique filename and save the file
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"
            image_path = os.path.join(category_folder, unique_filename)
            with open(image_path, "wb") as buffer:
                buffer.write(await file.read())

        # If only name is provided, add to ProductCategory
        if cleaned_category_name and not cleaned_parent_name:
            existing_category = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_category_name).first()
            if existing_category:
                raise HTTPException(status_code=400, detail="Category name already exists.", headers={"method": "POST", "path": "/apiv1/create-product-categories/"})
            
            # Create new product category
            product_count = db.query(func.count(ProductCategory.prodcat_id)).scalar()
            product_id = f"pcat_{product_count + 1}"
            db_category = ProductCategory(
                prodcat_id=product_id,
                prod_cat_name=cleaned_category_name,
                description=description, 
                prod_status=status, 
                imgthumbnail=image_path,
                status=False,
                timestamp=datetime.utcnow()
            )
            db.add(db_category)
            db.commit()
            db.refresh(db_category)
            return {
                "message": "Category created successfully",
                "category": db_category
            }

        # If both name and parent are provided
        if cleaned_category_name and cleaned_parent_name:
            # Check if the category already exists
            existing_category = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_category_name).first()
            if existing_category:
                existing_category_id = existing_category.prodcat_id

                # Check if the parent (subcategory) already exists under the same category
                existing_subcategory = db.query(ProductSubCategory).filter(
                    ProductSubCategory.prod_sub_name == cleaned_parent_name,
                    ProductSubCategory.prodcat_id == existing_category_id
                ).first()
                if existing_subcategory:
                    raise HTTPException(status_code=400, detail="Subcategory with the same name already exists under this category.", headers={"method": "POST", "path": "/apiv1/create-product-categories/"})

                # Create new subcategory under the existing category
                subcat_count = db.query(func.count(ProductSubCategory.product_sub_id)).scalar()
                subcat_id = f"psubcat_{subcat_count + 1}"

                db_subcategory = ProductSubCategory(
                    product_sub_id=subcat_id,
                    prodcat_id=existing_category_id,
                    prod_sub_name=cleaned_parent_name,
                    psub_status=status,
                    status=False,
                    timestamp=datetime.utcnow()
                )
                
                db.add(db_subcategory)
                db.commit()
                db.refresh(db_subcategory)

                return {
                    "message": "Subcategory created successfully under existing category",
                    "parent_category": existing_category,
                    "subcategory": db_subcategory
                }

            # If the parent category doesn't exist, create a new parent category and subcategory
            else:
                existing_parent = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_parent_name).first()
                if not existing_parent:
                    product_count = db.query(func.count(ProductCategory.prodcat_id)).scalar()
                    parent_id = f"pcat_{product_count + 1}"
                    db_parent = ProductCategory(
                        prodcat_id=parent_id,
                        prod_cat_name=cleaned_parent_name,
                        description=description,  # Add description from form data
                        prod_status=status,
                        imgthumbnail=image_path,  # Save the image path
                        status=False,
                        timestamp=datetime.utcnow()
                    )
                    db.add(db_parent)
                    db.commit()
                    db.refresh(db_parent)
                else:
                    parent_id = existing_parent.prodcat_id

                subcat_count = db.query(func.count(ProductSubCategory.product_sub_id)).scalar()
                subcat_id = f"psubcat_{subcat_count + 1}"

                db_subcategory = ProductSubCategory(
                    product_sub_id=subcat_id,
                    prodcat_id=parent_id,
                    prod_sub_name=cleaned_category_name,
                    psub_status=status,
                    status=False,
                    timestamp=datetime.utcnow()
                )
                db.add(db_subcategory)
                db.commit()
                db.refresh(db_subcategory)

                return {
                    "message": "Category and subcategory created successfully",
                    "parent_category": existing_parent if existing_parent else db_parent,
                    "subcategory": db_subcategory
                }

        # If only parent is provided, add the parent to ProductCategory
        if not cleaned_category_name and cleaned_parent_name:
            existing_parent = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_parent_name).first()
            if existing_parent:
                raise HTTPException(status_code=400, detail="Parent category already exists.", headers={"method": "POST", "path": "/apiv1/create-product-categories/"})
            
            product_count = db.query(func.count(ProductCategory.prodcat_id)).scalar()
            parent_id = f"pcat_{product_count + 1}"
            db_parent = ProductCategory(
                prodcat_id=parent_id,
                prod_cat_name=cleaned_parent_name,
                description=description,  # Add description from form data
                prod_status=status,
                imgthumbnail=image_path,  # Save the image path
                status=False,
                timestamp=datetime.utcnow()
            )
            db.add(db_parent)
            db.commit()
            db.refresh(db_parent)

            return {
                "message": "Parent category created successfully",
                "parent_category": db_parent
            }

    except HTTPException as e:
        # Forward any raised HTTPException with method and path included
        raise HTTPException(status_code=e.status_code, detail=e.detail, headers={"method": "POST", "path": "/apiv1/create-product-categories/"})
    except Exception as e:
        logger.error(f"Error creating product category or subcategory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating product category or subcategory: {e}", headers={"method": "POST", "path": "/apiv1/create-product-categories/"})


@router.get("/apiv1/get-categories/")
async def get_categories(db: Session = Depends(get_db)):
    try:
        categories = db.query(ProductCategory).all()
        if not categories:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "No categories found.",
                    "method": "GET",
                    "path": "/apiv1/get-categories/"
                }
            )
        
        category_data = []
        for category in categories:
            subcategories = db.query(ProductSubCategory).filter_by(prodcat_id=category.prodcat_id).all()
            category_data.append({
                "category_id": category.prodcat_id,
                "category_name": category.prod_cat_name,
                "description": category.description,  # Include category description
                "imgthumbnail": category.imgthumbnail,  # Include category image thumbnail
                "prod_status": category.status,
                "subcategories": [
                    {
                        "subcategory_id": sub.product_sub_id,
                        "subcategory_name": sub.prod_sub_name,
                        "psub_status": sub.status
                    }
                    for sub in subcategories
                ]
            })

        return {
            "message": "Categories and subcategories retrieved successfully.",
            "data": category_data
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error fetching categories: {str(e)}",
                "method": "GET",
                "path": "/apiv1/get-categories/"
            }
        )


@router.put("/apiv1/update-product-categories-details/{category_id}")
async def update_product_category(
    category_id: str,
    name: Optional[str] = Form(None),
    parent: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    status: Optional[bool] = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
       

        existing_category = db.query(ProductCategory).filter(ProductCategory.prodcat_id == category_id).first()
        if not existing_category:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Category not found.",
                    "method": "PUT",
                    "path": f"/apiv1/update-product-categories-details/{category_id}"
                }
            )

        cleaned_category_name = validate_name(name, "Category name").title() if name else existing_category.prod_cat_name
        cleaned_parent_name = validate_name(parent, "Parent name").title() if parent else None

        image_path = existing_category.imgthumbnail  
        if file:
            category_folder = os.path.join(UPLOAD_CATEGORY_FOLDER, cleaned_category_name or cleaned_parent_name)
            os.makedirs(category_folder, exist_ok=True)
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"
            image_path = os.path.join(category_folder, unique_filename)
            async with aiofiles.open(image_path, "wb") as buffer:
                await buffer.write(await file.read())

        if cleaned_category_name and not cleaned_parent_name:
            if cleaned_category_name != existing_category.prod_cat_name:
                existing_name = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_category_name).first()
                if existing_name:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "message": "Category name already exists.",
                            "method": "PUT",
                            "path": f"/apiv1/update-product-categories-details/{category_id}"
                        }
                    )

            existing_category.prod_cat_name = cleaned_category_name
            if description:
                existing_category.description = description
            existing_category.prod_status = status if status is not None else existing_category.prod_status
            if file:
                existing_category.imgthumbnail = image_path
            db.commit()
            db.refresh(existing_category)
            return {"message": "Category updated successfully", "category": existing_category}

        if cleaned_category_name and cleaned_parent_name:
            existing_parent = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_parent_name).first()
            if not existing_parent:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": "Parent category not found.",
                        "method": "PUT",
                        "path": f"/apiv1/update-product-categories-details/{category_id}"
                    }
                )

            existing_subcategory = db.query(ProductSubCategory).filter(
                ProductSubCategory.prod_sub_name == cleaned_category_name,
                ProductSubCategory.prodcat_id == existing_parent.prodcat_id
            ).first()

            if existing_subcategory and existing_subcategory.product_sub_id != category_id:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Subcategory with the same name already exists under this parent.",
                        "method": "PUT",
                        "path": f"/apiv1/update-product-categories-details/{category_id}"
                    }
                )

            subcategory = db.query(ProductSubCategory).filter(ProductSubCategory.product_sub_id == category_id).first()
            if subcategory:
                subcategory.prod_sub_name = cleaned_category_name
                subcategory.prodcat_id = existing_parent.prodcat_id
                subcategory.psub_status = status if status is not None else subcategory.psub_status
                db.commit()
                db.refresh(subcategory)
                return {"message": "Subcategory updated successfully", "subcategory": subcategory}
            else:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": "Subcategory not found.",
                        "method": "PUT",
                        "path": f"/apiv1/update-product-categories-details/{category_id}"
                    }
                )

        if not cleaned_category_name and cleaned_parent_name:
            existing_parent = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == cleaned_parent_name).first()
            if existing_parent:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "Parent category already exists.",
                        "method": "PUT",
                        "path": f"/apiv1/update-product-categories-details/{category_id}"
                    }
                )

            existing_category.prod_cat_name = cleaned_parent_name
            if description:
                existing_category.description = description
            existing_category.prod_status = status if status is not None else existing_category.prod_status
            if file:
                existing_category.imgthumbnail = image_path
            db.commit()
            db.refresh(existing_category)

            return {
                "message": "Parent category updated successfully",
                "category": existing_category
            }

        return {"message": "No updates were made."}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating product category or subcategory: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error updating product category or subcategory: {str(e)}",
                "method": "PUT",
                "path": f"/apiv1/update-product-categories-details/{category_id}"
            }
        )

@router.delete("/apiv1/delete-product-categories/{product_id}")
async def delete_product_category(product_id: str, db: Session = Depends(get_db)):
    try:
      
        
        db_category = db.query(ProductCategory).filter(ProductCategory.prodcat_id == product_id).first()
        if db_category is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "ProductCategory not found",
                    "method": "DELETE",
                    "path": f"/apiv1/delete-product-categories/{product_id}"
                }
            )

        db_category.status = True
        db.commit()
        return {"detail": "ProductCategory deleted successfully"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting product category: {str(e)}")
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error deleting product category",
                "method": "DELETE",
                "path": f"/apiv1/delete-product-categories/{product_id}"
            }
        )




@router.put("/update_product_cat_status/{prodcat_id}", )
async def update_status(
    prodcat_id: str, 
    status_update: StatusUpdate, 
    db: Session = Depends(get_db)
):
    try:
       

        # Fetch the product category
        product_category = db.query(ProductCategory).filter(ProductCategory.prodcat_id == prodcat_id).first()
        
        if not product_category:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Product Category not found",
                    "method": "PUT",
                    "path": f"/update_product_cat_status/{prodcat_id}"
                }
            )
        
        product_category.prod_status = status_update.status
        subcategories = db.query(ProductSubCategory).filter(ProductSubCategory.prodcat_id == prodcat_id).all()
        if subcategories:
            for subcategory in subcategories:
                subcategory.psub_status = status_update.status
        db.commit()
        return JSONResponse(
            status_code=200,
            content={
                "message": "Status updated successfully",
                "method": "PUT",
                "path": f"/update_product_cat_status/{prodcat_id}",
                "status_updated_to": status_update.status
            }
        )
    except SQLAlchemyError as e:
        # Rollback in case of an error
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error updating product category or subcategory: {str(e)}",
                "method": "PUT",
                "path": f"/update_product_cat_status/{prodcat_id}"
            }
        )
    
    except Exception as e:
        # Catch any other exceptions and raise a custom error message
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"An unexpected error occurred: {str(e)}",
                "method": "PUT",
                "path": f"/update_product_cat_status/{prodcat_id}"
            }
        )