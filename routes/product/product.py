
import csv
from datetime import datetime
import io
from fastapi import APIRouter, Depends, HTTPException,File, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.product_models import ProductCategory, ProductSubCategory, ProductUpdate, ProductionTable,ProductCreate, StatusUpdate, Stock
from utils import get_db # type: ignore
from config import logger # type: ignore
from redis_util  import get_redis, rate_limiter,RATE_LIMIT_DURATION,MAX_ATTEMPTS
from fastapi.responses import JSONResponse
from models.user_models import Configuration
import os
from uuid import uuid4
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(tags=["product"])

def generate_id(db: Session, entity: str):
    config = db.query(Configuration).first()
    if not config:
        raise HTTPException(status_code=400, detail="Configuration not found")
    if entity == "production_table":
        prefix = config.productionid
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")

    new_id = f"{prefix}{config.prodincrement}"
    config.prodincrement += config.prodincrement
    return new_id

import re
def validate_name(name: str, field_name: str) -> str:
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty.")
    cleaned_name = name.strip()
    if not re.match("^[a-zA-Z ]+$", cleaned_name):
        raise HTTPException(status_code=400, detail=f"{field_name} should only contain alphabetic characters.")
    return cleaned_name.title()

def validate_title_or_description(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise HTTPException(status_code=400, detail=f"{field_name} cannot be empty.")
    cleaned_value = value.strip()
    if not re.match("^[a-zA-Z0-9 ]+$", cleaned_value):
        raise HTTPException(status_code=400, detail=f"{field_name} should not contain special characters.")
    return cleaned_value

def validate_actualprice(actualprice: str) -> float:
    if not actualprice:
        raise HTTPException(status_code=400, detail="actualprice cannot be empty.")
    try:
        actualprice_value = float(actualprice)
        if actualprice_value <= 0:
            raise ValueError("actualprice must be positive.")
    except ValueError:
        raise HTTPException(status_code=400, detail="actualprice must be a positive number.")
    return actualprice_value


# @router.post("/apiv1/upload-products/")
# async def upload_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     content = await file.read()
#     try:
#         cleaned_content = content.decode('utf-8').replace('\x00', '')
#         csv_reader = csv.reader(io.StringIO(cleaned_content), delimiter=',', quotechar='"')
#         headers = next(csv_reader)  # Extract headers
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "message": f"Error processing the CSV file: {str(e)}",
#                 "method": "POST",
#                 "path": "/apiv1/upload-products/"
#             }
#         )
    
#     expected_headers = ['prod_cat_name', 'prod_sub_name', 'title', 'description', 'shortdescription', 'actualprice', 'sellingprice', 'sku','stockquantity','pimg1', 'pimg2', 'pimg3', 'pimg4', 'pimg5']
    
#     if headers != expected_headers:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "message": "CSV file does not have the correct headers.",
#                 "method": "POST",
#                 "path": "/apiv1/upload-products/"
#             }
#         )
    
#     category_cache = {}
#     subcategory_cache = {}
#     last_category_name = None 

#     for row in csv_reader:
#         if not row:
#             continue 

#         if len(row) < len(expected_headers):
#             raise HTTPException(
#                 status_code=400,
#                 detail={
#                     "message": "Row does not have the correct number of columns.",
#                     "method": "POST",
#                     "path": "/apiv1/upload-products/"
#                 }
#             )
        
#         prod_cat_name, prod_sub_name, title, description, shortdescription, actualprice, sellingprice,sku,stockquantity, pimg1, pimg2, pimg3, pimg4, pimg5 = map(str.strip, row)

#         if not prod_cat_name:
#             prod_cat_name = last_category_name
#         else:
#             last_category_name = prod_cat_name

#         if prod_cat_name not in category_cache:
#             existing_category = db.query(ProductCategory).filter_by(prod_cat_name=prod_cat_name).first()
#             if existing_category:
#                 product_id = existing_category.prodcat_id
#             else:
#                 product_count = db.query(func.count(ProductCategory.prodcat_id)).scalar()
#                 product_id = f"pcat_{product_count + 1}"
#                 product_category = ProductCategory(
#                     prodcat_id=product_id,
#                     prod_cat_name=prod_cat_name,
#                     status=False,
#                     timestamp=datetime.utcnow()
#                 )
#                 db.add(product_category)
#                 db.commit()
#                 db.refresh(product_category)

#             category_cache[prod_cat_name] = product_id
#         else:
#             product_id = category_cache[prod_cat_name]

#         cache_key = f"{prod_cat_name}_{prod_sub_name}"
#         if cache_key not in subcategory_cache:
#             existing_subcategory = db.query(ProductSubCategory).filter_by(prod_sub_name=prod_sub_name, prodcat_id=product_id).first()
#             if existing_subcategory:
#                 product_sub_id = existing_subcategory.product_sub_id
#             else:
#                 prodsub_count = db.query(func.count(ProductSubCategory.product_sub_id)).scalar()
#                 product_sub_id = f"psubcat_{prodsub_count + 1}"

#                 product_subcategory = ProductSubCategory(
#                     product_sub_id=product_sub_id,
#                     prodcat_id=product_id,
#                     prod_sub_name=prod_sub_name,
#                     status=False,
#                     timestamp=datetime.utcnow()
#                 )
#                 db.add(product_subcategory)
#                 db.commit()
#                 db.refresh(product_subcategory)

#             subcategory_cache[cache_key] = product_sub_id
#         else:
#             product_sub_id = subcategory_cache[cache_key]

#         existing_product = db.query(ProductionTable).filter_by(
#             prodcat_id=product_id,
#             product_sub_id=product_sub_id,
#             title=title
#         ).first()

#         if existing_product:
#             continue 

#         production_count = db.query(func.count(ProductionTable.production_id)).scalar()
#         production_id = f"prod_{production_count + 1}"
#         production = ProductionTable(
#             production_id=production_id,
#             prodcat_id=product_id,
#             product_sub_id=product_sub_id,
#             title=title,
#             description=description,
#             shortdescription=shortdescription,
#             actualprice=actualprice,
#             linkedproductid=production_id,
#             sellingprice=sellingprice,
#             pimg1=pimg1 if pimg1 else None,
#             pimg2=pimg2 if pimg2 else None,
#             pimg3=pimg3 if pimg3 else None,
#             pimg4=pimg4 if pimg4 else None,
#             pimg5=pimg5 if pimg5 else None
#         )
#         db.add(production)

#     try:
#         db.commit()  
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=500,
#             detail={
#                 "message": f"Failed to commit to the database: {str(e)}",
#                 "method": "POST",
#                 "path": "/apiv1/upload-products/"
#             }
#         )

#     return {"message": "Products uploaded successfully."}

@router.post("/apiv1/upload-products/")
async def upload_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        cleaned_content = content.decode('utf-8').replace('\x00', '')
        csv_reader = csv.reader(io.StringIO(cleaned_content), delimiter=',', quotechar='"')
        headers = next(csv_reader)  # Extract headers
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Error processing the CSV file: {str(e)}",
                "method": "POST",
                "path": "/apiv1/upload-products/"
            }
        )
    
    expected_headers = ['prod_cat_name', 'prod_sub_name', 'title', 'description', 'shortdescription', 'actualprice', 'sellingprice', 'sku', 'stockquantity', 'pimg1', 'pimg2', 'pimg3', 'pimg4', 'pimg5']
    
    if headers != expected_headers:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "CSV file does not have the correct headers.",
                "method": "POST",
                "path": "/apiv1/upload-products/"
            }
        )
    
    category_cache = {}
    subcategory_cache = {}
    last_category_name = None 

    for row in csv_reader:
        if not row:
            continue 

        if len(row) < len(expected_headers):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Row does not have the correct number of columns.",
                    "method": "POST",
                    "path": "/apiv1/upload-products/"
                }
            )
        
        prod_cat_name, prod_sub_name, title, description, shortdescription, actualprice, sellingprice, sku, stockquantity, pimg1, pimg2, pimg3, pimg4, pimg5 = map(str.strip, row)

        if not prod_cat_name:
            prod_cat_name = last_category_name
        else:
            last_category_name = prod_cat_name

        if prod_cat_name not in category_cache:
            existing_category = db.query(ProductCategory).filter_by(prod_cat_name=prod_cat_name).first()
            if existing_category:
                product_id = existing_category.prodcat_id
            else:
                product_count = db.query(func.count(ProductCategory.prodcat_id)).scalar()
                product_id = f"pcat_{product_count + 1}"
                product_category = ProductCategory(
                    prodcat_id=product_id,
                    prod_cat_name=prod_cat_name,
                    status=False,
                    timestamp=datetime.utcnow()
                )
                db.add(product_category)
                db.commit()
                db.refresh(product_category)

            category_cache[prod_cat_name] = product_id
        else:
            product_id = category_cache[prod_cat_name]

        cache_key = f"{prod_cat_name}_{prod_sub_name}"
        if cache_key not in subcategory_cache:
            existing_subcategory = db.query(ProductSubCategory).filter_by(prod_sub_name=prod_sub_name, prodcat_id=product_id).first()
            if existing_subcategory:
                product_sub_id = existing_subcategory.product_sub_id
            else:
                prodsub_count = db.query(func.count(ProductSubCategory.product_sub_id)).scalar()
                product_sub_id = f"psubcat_{prodsub_count + 1}"

                product_subcategory = ProductSubCategory(
                    product_sub_id=product_sub_id,
                    prodcat_id=product_id,
                    prod_sub_name=prod_sub_name,
                    status=False,
                    timestamp=datetime.utcnow()
                )
                db.add(product_subcategory)
                db.commit()
                db.refresh(product_subcategory)

            subcategory_cache[cache_key] = product_sub_id
        else:
            product_sub_id = subcategory_cache[cache_key]

        existing_product = db.query(ProductionTable).filter_by(
            prodcat_id=product_id,
            product_sub_id=product_sub_id,
            title=title
        ).first()

        if existing_product:
            continue 

        production_count = db.query(func.count(ProductionTable.production_id)).scalar()
        production_id = f"prod_{production_count + 1}"
        production = ProductionTable(
            production_id=production_id,
            prodcat_id=product_id,
            product_sub_id=product_sub_id,
            title=title,
            description=description,
            shortdescription=shortdescription,
            actualprice=actualprice,
            linkedproductid=production_id,
            sellingprice=sellingprice,
            pimg1=pimg1 if pimg1 else None,
            pimg2=pimg2 if pimg2 else None,
            pimg3=pimg3 if pimg3 else None,
            pimg4=pimg4 if pimg4 else None,
            pimg5=pimg5 if pimg5 else None
        )
        db.add(production)

        # Adding stock information
        stock = Stock(
            stockid=sku,  # Assuming SKU is unique and used as stock ID
            productid=production_id,  # Link to the newly created product
            stockquantity=stockquantity  # Set the stock quantity
        )
        db.add(stock)

    try:
        db.commit()  
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Failed to commit to the database: {str(e)}",
                "method": "POST",
                "path": "/apiv1/upload-products/"
            }
        )

    return {"message": "Products uploaded successfully."}



@router.post("/apiv1/create-product/")
async def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    try:
        
        # Generate production_id dynamically based on the total number of products
        production_count = db.query(func.count(ProductionTable.production_id)).scalar()
        production_id = f"prod_{production_count + 1}"
        db_product = ProductionTable(
            prodcat_id=product.prod_cat_id,
            product_sub_id=product.prod_sub_cat_id,
            production_id=production_id,
            title=product.title,
            description=product.description,
            actualprice=product.actualprice,
            sellingprice=product.sellingprice,
            shortdescription=product.shortdescription,
            linkedproductid=product.linkedproductid,
            pstatus=product.status
        )
        db.add(db_product)
        db_stock = Stock(
            stockid=product.skuid, 
            productid=production_id,  
            stockquantity=product.stockquantity,
        )
        db.add(db_stock)
        db.commit()
        db.refresh(db_product)
        return {"product": db_product, "stock": db_stock}

    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": f"Error creating production {e}",
            "method": "POST",
            "path": "/apiv1/create-product/"
        })

UPLOAD_ROOT_FOLDER = 'production_images/'
if not os.path.exists(UPLOAD_ROOT_FOLDER):
    os.makedirs(UPLOAD_ROOT_FOLDER)

@router.post("/apiv1/upload-product-images/")
async def upload_production_images(
    product_id: str,
    file1: UploadFile = File(None),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    file4: UploadFile = File(None),
    file5: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    
    
    # Check if the ProductionTable with the given production_id exists
    production = db.query(ProductionTable).filter(ProductionTable.production_id == product_id).first()
    if not production:
        raise HTTPException(status_code=404, detail={
            "message": "Production not found",
            "method": "POST",
            "path": "/apiv1/upload-product-images/"
        })
    
    # Create a folder for the production_id if it doesn't exist
    production_folder = os.path.join(UPLOAD_ROOT_FOLDER, product_id)
    if not os.path.exists(production_folder):
        os.makedirs(production_folder)
    
    file_list = [file1, file2, file3, file4, file5]
    file_paths = []
    for i, file in enumerate(file_list):
        if file:
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"
            file_path = os.path.join(production_folder, unique_filename)

            # Write the file to the designated path
            with open(file_path, "wb") as buffer:
                buffer.write(await file.read())

            file_paths.append(file_path)
            if i == 0:
                production.pimg1 = file_path
            elif i == 1:
                production.pimg2 = file_path
            elif i == 2:
                production.pimg3 = file_path
            elif i == 3:
                production.pimg4 = file_path
            elif i == 4:
                production.pimg5 = file_path

    # Commit changes to the database
    db.commit()
    return {"message": "Production images uploaded successfully", "file_paths": file_paths}


@router.get("/apiv1/get-productdetails-by-id/{product_id}")
async def get_product_by_id(product_id: str, db: Session = Depends(get_db)):
    try:
        

        product = db.query(
            ProductionTable.production_id,
            ProductionTable.prodcat_id,
            ProductionTable.product_sub_id,
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
            ProductionTable.pstatus,
            ProductionTable.status,
            ProductionTable.timestamp,
            Stock.stockid,
            Stock.stockquantity
        ).outerjoin(Stock, Stock.productid == ProductionTable.production_id) \
         .filter(ProductionTable.production_id == product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail={
                "message": f"Product with ID '{product_id}' not found.",
                "method": "GET",
                "path": f"/apiv1/get-productdetails-by-id/{product_id}"
            })

        # Structure the response with product and stock details included
        return {
            "production_id": product.production_id,
            "prodcat_id": product.prodcat_id,
            "product_sub_id": product.product_sub_id,
            "title": product.title,
            "description": product.description,
            "shortdescription": product.shortdescription,
            "actualprice": product.actualprice,
            "sellingprice": product.sellingprice,
            "pimg1": product.pimg1,
            "pimg2": product.pimg2,
            "pimg3": product.pimg3,
            "pimg4": product.pimg4,
            "pimg5": product.pimg5,
            "pstatus": product.pstatus,
            "status": product.status,
            "timestamp": product.timestamp,
            "stockid": product.stockid,  # Adding stock ID
            "stockquantity": product.stockquantity  # Adding stock quantity
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": f"An unexpected error occurred: {str(e)}",
            "method": "GET",
            "path": f"/apiv1/get-productdetails-by-id/{product_id}"
        })
    
@router.get("/apiv1/get-all-products/")
async def get_all_products(db: Session = Depends(get_db)):
    try:
        

        # Query to get all product details along with stock information
        products = db.query(
            ProductionTable.production_id,
            ProductionTable.prodcat_id,
            ProductionTable.product_sub_id,
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
            ProductionTable.pstatus,
            ProductionTable.status,
            ProductionTable.timestamp,
            Stock.stockid,
            Stock.stockquantity
        ).outerjoin(Stock, Stock.productid == ProductionTable.production_id).all()

        # If no products are found, return an empty list
        if not products:
            return []  # Return an empty list when no products are found

        # Structure the response with product and stock details included
        product_list = []
        for product in products:
            product_list.append({
                "production_id": product.production_id,
                "prodcat_id": product.prodcat_id,
                "product_sub_id": product.product_sub_id,
                "title": product.title,
                "description": product.description,
                "shortdescription": product.shortdescription,
                "actualprice": product.actualprice,
                "sellingprice": product.sellingprice,
                "linkedproductid": product.linkedproductid,
                "pimg1": product.pimg1,
                "pimg2": product.pimg2,
                "pimg3": product.pimg3,
                "pimg4": product.pimg4,
                "pimg5": product.pimg5,
                "pstatus": product.pstatus,
                "status": product.status,
                "timestamp": product.timestamp,
                "stockid": product.stockid,  # Adding stock ID
                "stockquantity": product.stockquantity  # Adding stock quantity
            })

        return product_list

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "message": f"An unexpected error occurred: {str(e)}",
            "method": "GET",
            "path": "/apiv1/get-all-products/"
        })


@router.get("/apiv1/get-product/{production_id}/images/")
async def get_product_images(
    production_id: str,
    db: Session = Depends(get_db)
):
    try:
        # Assuming you have a Redis rate limiter in place
       

        production = db.query(ProductionTable).filter(ProductionTable.production_id == production_id).first()
        if not production:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Product not found",
                    "method": "GET",
                    "path": "/apiv1/get-product/{production_id}/images/"
                }
            )

        image_urls = []
        for i in range(1, 6):  # Assuming pimg1 to pimg5
            image_field = f"pimg{i}"
            image_path = getattr(production, image_field)
            if image_path and os.path.exists(image_path):
                # Generate URL for the image
                image_url = f"/static/{production_id}/{os.path.basename(image_path)}"
                image_urls.append(image_url)

        # Instead of raising an error, return an empty list if no images found
        return JSONResponse(content={"image_urls": image_urls})

    except Exception as e:
        logger.error(f"Error fetching product images: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "An unexpected error occurred",
                "method": "GET",
                "path": "/apiv1/get-product/{production_id}/images/"
            }
        )

@router.put("/apiv1/update-product/{product_id}")
async def update_product(product_id: str, product: ProductUpdate, db: Session = Depends(get_db)):
    try:
        

        # Fetch the existing product
        existing_product = db.query(ProductionTable).filter(ProductionTable.production_id == product_id).first()

        # Check if the product exists
        if not existing_product:
            raise HTTPException(status_code=404, detail={
                "message": f"Product with ID '{product_id}' not found.",
                "method": "PUT",
                "path": f"/apiv1/update-product/{product_id}"
            })

        # Update only the fields that were provided
        if product.prod_cat_id is not None:
            existing_product.prodcat_id = product.prod_cat_id
        if product.prod_sub_cat_id is not None:
            existing_product.product_sub_id = product.prod_sub_cat_id
        if product.title is not None and product.title != '':
            existing_product.title = product.title
        if product.description is not None and product.description != '':
            existing_product.description = product.description
        if product.shortdescription is not None and product.shortdescription != '':
            existing_product.shortdescription = product.shortdescription
        if product.actualprice is not None and product.actualprice != '':
            existing_product.actualprice = product.actualprice
        if product.sellingprice is not None and product.sellingprice != '':
            existing_product.sellingprice = product.sellingprice
        if product.status is not None:
            existing_product.pstatus = product.status

        # If stock details need to be updated, fetch the stock and update it
        if product.skuid is not None or product.stockquantity is not None:
            db_stock = db.query(Stock).filter(Stock.productid == product_id).first()
            if db_stock:
                if product.skuid is not None:
                    db_stock.stockid = product.skuid
                if product.stockquantity is not None:
                    db_stock.stockquantity = product.stockquantity

        db.commit()
        db.refresh(existing_product)

        return {"product": existing_product}

    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "message": f"Error updating product: {e}",
            "method": "PUT",
            "path": f"/apiv1/update-product/{product_id}"
        })



@router.delete("/apiv1/delete-product/{product_id}")
async def delete_production(product_id: str, db: Session = Depends(get_db)):
    try:
        
  
        db_production = db.query(ProductionTable).filter(ProductionTable.production_id == product_id).first()
        if db_production is None:
            raise HTTPException(status_code=404, detail={
                "message": "Production not found",
                "method": "DELETE",
                "path": f"/apiv1/delete-product/{product_id}"
            })
        
        db_production.status = True
        db.commit()
        return {"detail": "Production deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting production: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail={
            "message": "Error deleting production",
            "method": "DELETE",
            "path": f"/apiv1/delete-product/{product_id}"
        })
    



@router.put("/update_product_status/{product_id}")
def update_product_status(
    product_id: str, 
    status_update: StatusUpdate,  # Expects a body with the status field
    db: Session = Depends(get_db)
):
    try:
        # Fetch the product by its production_id
        product = db.query(ProductionTable).filter(ProductionTable.production_id == product_id).first()

        if not product:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "Product not found",
                    "method": "PUT",
                    "path": f"/update_product_status/{product_id}"
                }
            )
        
        # Update the product status
        product.pstatus = status_update.status
        
        # Commit the changes
        db.commit()

        # Return a successful response
        return {
            "message": "Product status updated successfully",
            "method": "PUT",
            "path": f"/update_product_status/{product_id}",
            "status_updated_to": status_update.status
        }

    except SQLAlchemyError as e:
        # Rollback in case of an error
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error updating product status: {str(e)}",
                "method": "PUT",
                "path": f"/update_product_status/{product_id}"
            }
        )

    except Exception as e:
        # Catch any other exceptions and raise a custom error message
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"An unexpected error occurred: {str(e)}",
                "method": "PUT",
                "path": f"/update_product_status/{product_id}"
            }
        )