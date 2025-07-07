from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi import HTTPException
from utils import get_db
from models.product_models import ProductSubCategory,ProductCategory,ProductionTable 
from config import logger
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from sqlalchemy.exc import SQLAlchemyError
router = APIRouter(tags=["admin_products"])

from fastapi import Request

@router.get("/apiv1/product-subcategories/")
async def read_all_product_subcategories(request: Request, db: Session = Depends(get_db)):
    try:
       
        subcategories = db.query(ProductSubCategory, ProductCategory).join(ProductSubCategory.category).filter(
            ProductSubCategory.status == False
        ).all()

        result = []
        for subcategory, category in subcategories:
            result.append({
                "prod_sub_name": subcategory.prod_sub_name,
                "prodcat_id": subcategory.prodcat_id,
                "product_name": category.prod_cat_name,  # Include product category name
                "timestamp": subcategory.timestamp,
                "status": subcategory.status,
                "product_sub_id": subcategory.product_sub_id
            })
        
        return result

    except HTTPException as http_exc:
        # Log HTTPException with method and path
        logger.error(f"HTTP Exception: {http_exc.detail} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=http_exc.status_code, detail=f"{http_exc.detail}. Method: {request.method}, Path: {request.url.path}")
    
    except Exception as e:
        # Log other exceptions with method and path
        logger.error(f"Error reading product subcategories: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error reading product subcategories.{e} Method: {request.method}, Path: {request.url.path}")

@router.get("/apiv1/category-count/")
async def get_category_count(request: Request, db: Session = Depends(get_db)):
    try:
        # Fetch all categories
        categories = db.query(ProductCategory).all()
        
        # Prepare the response with category details
        category_details = [
            {
                "category_id": category.prodcat_id,
                "category_name": category.prod_cat_name,
                "description": category.description,
                "image_thumbnail": category.imgthumbnail,
                "status": category.prod_status,
                "timestamp": category.timestamp
            }
            for category in categories
        ]
        
        return {
            "total_categories": len(categories),
            "categories": category_details
        }
    
    except Exception as e:
        # Log and raise HTTPException with method and path
        logger.error(f"Error fetching category details: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"Error fetching category details. Method: {request.method}, Path: {request.url.path}")
    
@router.get("/apiv1/subcategories-count/")
async def get_subcategory_details(request: Request, db: Session = Depends(get_db)):
    try:
        subcategories = db.query(ProductSubCategory).all()
        subcategory_count = len(subcategories)
        return {
            "total_subcategories": subcategory_count,
            "subcategories": [subcategory.prod_sub_name for subcategory in subcategories]
        }
    except Exception as e:
        # Log and raise HTTPException with method and path
        logger.error(f"Error fetching subcategory details: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"Error fetching subcategory details. Method: {request.method}, Path: {request.url.path}")
    
@router.get("/apiv1/get-all-products/")
async def get_all_productions(request: Request, db: Session = Depends(get_db)):
   
    try:
        productions = db.query(
            ProductionTable.production_id,
            ProductionTable.title,
            ProductionTable.description,
            ProductionTable.shortdescription,
            ProductionTable.actualprice,
            ProductionTable.sellingprice,
            ProductionTable.pimg1,
            ProductionTable.pimg2,
            ProductionTable.pimg3,
            ProductionTable.pimg4,
            ProductionTable.pimg5,
            ProductionTable.status,
            ProductionTable.timestamp,
            ProductCategory.prodcat_id,
            ProductCategory.prod_cat_name,
            ProductSubCategory.product_sub_id,
            ProductSubCategory.prod_sub_name
        ).join(
            ProductCategory, ProductionTable.prodcat_id == ProductCategory.prodcat_id
        ).join(
            ProductSubCategory, ProductionTable.product_sub_id == ProductSubCategory.product_sub_id
        ).all()

        # If no productions are found, return an empty list
        if not productions:
            logger.info(f"No productions found - Method: {request.method}, Path: {request.url.path}")
            return []  # Return an empty list when no products are found

        return [
            {
                "production_id": production.production_id,
                "title": production.title,
                "description": production.description,
                "shortdescription": production.shortdescription,
                "actualprice": production.actualprice,
                "sellingprice": production.sellingprice,
                "pimg1": production.pimg1,
                "pimg2": production.pimg2,
                "pimg3": production.pimg3,
                "pimg4": production.pimg4,
                "pimg5": production.pimg5,
                "status": production.status,
                "timestamp": production.timestamp,
                "prodcat_id": production.prodcat_id,
                "product_name": production.prod_cat_name,
                "product_sub_id": production.product_sub_id,
                "prod_sub_name": production.prod_sub_name
            }
            for production in productions
        ]
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error occurred: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"Database error occurred. Method: {request.method}, Path: {request.url.path}")

    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred. {str(e)} Method: {request.method}, Path: {request.url.path}")

    
@router.get("/apiv1/get-all-sub-products-by/{prod_cat_name}")
async def get_products_by_category(prod_cat_name: str, request: Request, db: Session = Depends(get_db)):
    try:
        category = db.query(ProductCategory).filter(ProductCategory.prod_cat_name == prod_cat_name).first()
        if not category:
            logger.error(f"Product category '{prod_cat_name}' not found - Method: {request.method}, Path: {request.url.path}")
            raise HTTPException(status_code=404, detail=f"Product category '{prod_cat_name}' not found. Method: {request.method}, Path: {request.url.path}")
        
        subcategories = (
            db.query(
                ProductSubCategory.prod_sub_name,
                ProductionTable.title,
                ProductionTable.description,
                ProductionTable.shortdescription,
                ProductionTable.actualprice,
                ProductionTable.sellingprice
            )
            .join(ProductionTable, ProductSubCategory.product_sub_id == ProductionTable.product_sub_id)
            .filter(ProductSubCategory.prodcat_id == category.prodcat_id)
            .all()
        )

        if not subcategories:
            logger.error(f"No products found for category '{prod_cat_name}' - Method: {request.method}, Path: {request.url.path}")
            return {"message": f"No products found for category '{prod_cat_name}'."}

        result = {
            "category": prod_cat_name,
            "products": []
        }

        for subcategory, title, description, shortdescription, actualprice, sellingprice in subcategories:
            result["products"].append({
                "subcategory": subcategory,
                "title": title,
                "description": description,
                "shortdescription": shortdescription,
                "actualprice": actualprice,
                "sellingprice": sellingprice
            })

        return result
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error occurred: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"Database error occurred. Method: {request.method}, Path: {request.url.path}")
    
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)} - Method: {request.method}, Path: {request.url.path}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred. Method: {request.method}, Path: {request.url.path}")
