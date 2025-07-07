from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import warnings
from fastapi.middleware.cors import CORSMiddleware
warnings.filterwarnings("ignore") 
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from routes.usermanagement import user_registation,user_login,user_profile
from config import logger
from routes.product import product, product_cat,store,role
from routes.admin import create_admin_user, internal_details,admin_products,userdetails
from fastapi import FastAPI

app = FastAPI()



tags_metadata = [
    {
        "name":"Admin User Creation",
        "description":"Operations related to the admin user"
    },
     {
        "name":"internal_details",
        "description":"Operations related to the internal details"
    },
    {
        "name":"user_details",
        "description":"Operations related to the user details"
    },
    {
        "name":"admin_products",
        "description":"Operations related to the products"
    },
    {
        "name": "user_registation",
        "description": "Operations related to vendor registatrion",
    },
    {
        "name":"user_login",
        "description":"Operations related to the login"
    },
    {
        "name":"user_profile",
        "description":"Operations related to the user profile"
    },
    {
        "name":"product_cat",
        "description":"Operations related to the product category"
    },
    {
        "name":"product",
        "description":"Operations related to the product"
    },
    {
        "name":"store",
        "description":"Operations related to the store"
    },
    {
        "name":"Roles",
        "description":"Operations related to the role"
    }
   
]
   

app = FastAPI(
    title="Ecommerce",
    openapi_url="/Ecommerce.json",
    version="1.0.1",
    description="Ecommerce APIs",
    redoc_url="/redoc/",  # Disable Redoc (built-in docs)
    docs_url="/docs/",  # Define a custom endpoint for docs
    openapi_tags=tags_metadata,  # Use the custom tags defined here
)

# Allow CORS for development (customize origins as needed)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    GZipMiddleware,
    minimum_size=1000  # Adjust as needed
)

logger.info("Starting FastAPI application...")

# API routes from User Management
app.include_router(create_admin_user.admin_router)
app.include_router(internal_details.router)
app.include_router(userdetails.router)
app.include_router(admin_products.router)
app.include_router(user_registation.router)
app.include_router(user_login.router)
app.include_router(user_profile.router)
app.include_router(product_cat.router)
app.include_router(product.router)
app.include_router(store.router)
app.include_router(role.router)

# Custom exception handler to handle exceptions globally
async def custom_exception_handler(request, exc):
    # Log the exception
    logger.error(f"An error occurred: {str(exc)}")

    # You can add custom logic here to create an appropriate response
    # For example, check the type of exception and return a specific response
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    # For other exceptions, you can return a generic error response
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


app.add_exception_handler(Exception, custom_exception_handler)

# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=8073)
