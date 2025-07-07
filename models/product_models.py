from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func, Sequence,Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field, validator
from typing import Optional
from sqlalchemy import text

Base = declarative_base()

class ProductCategory(Base):
    __tablename__ = 'product_category'

    prodcat_id = Column(String, primary_key=True, unique=True)
    prod_cat_name = Column(String, nullable=False)
    description = Column(String)
    imgthumbnail = Column(String)
    prod_status=Column(Boolean)
    status = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    subcategories = relationship('ProductSubCategory', back_populates='category')
    productions = relationship('ProductionTable', back_populates='product_category')

class ProductSubCategory(Base):
    __tablename__ = 'product_subcategory'

    product_sub_id = Column(String, primary_key=True, unique=True)
    prodcat_id = Column(String, ForeignKey('product_category.prodcat_id'), nullable=False)
    prod_sub_name = Column(String, nullable=False)
    psub_status = Column(Boolean)
    status = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    category = relationship('ProductCategory', back_populates='subcategories')
    productions = relationship('ProductionTable', back_populates='product_subcategory')

class ProductionTable(Base):
    __tablename__ = 'product_table'
    production_id = Column(String, primary_key=True,unique=True)
    prodcat_id = Column(String, ForeignKey('product_category.prodcat_id'), nullable=False)
    product_sub_id = Column(String, ForeignKey('product_subcategory.product_sub_id'), nullable=False)
    title = Column(String)
    description = Column(String)
    shortdescription = Column(String)
    actualprice = Column(String)
    sellingprice=Column(String)
    linkedproductid = Column(String)
    pimg1=Column(String)
    pimg2=Column(String)
    pimg3=Column(String)
    pimg4=Column(String)
    pimg5=Column(String)
    pstatus=Column(String)
    status = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    product_category = relationship('ProductCategory', back_populates='productions')
    product_subcategory = relationship('ProductSubCategory', back_populates='productions')
    

class Stock(Base):
    __tablename__ = 'stock'
    
    stockid = Column(String, primary_key=True)
    productid = Column(String, nullable=True)
    stockquantity = Column(String, nullable=True)
    status = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)



class StoreSettings(Base):
    __tablename__ = 'store_settings'

    storeid = Column(String, primary_key=True, unique=True)
    addressline1 = Column(String, nullable=False)
    addressline2 = Column(String, nullable=True)
    country = Column(String, nullable=False)
    state = Column(String, nullable=False)
    city = Column(String, nullable=False)
    postcode = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    currencypostion = Column(String, nullable=False)
    status = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class StoreSettingsCreate(BaseModel):
    addressline1: str 
    addressline2: Optional[str] = None
    country: str 
    state: str 
    city: str 
    postcode: str 
    currency: str 
    currencypostion: str 
    status: Optional[bool] =False

class StoreSettingsUpdate(BaseModel):
    addressline1: Optional[str] = None
    addressline2: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    currency: Optional[str] = None
    currencypostion: Optional[str] = None
    status: Optional[bool] = None

class ProductCategoryCreate(BaseModel):
    name: Optional[str] = ''
    parent:Optional[str] = ''
    description: Optional[str] = ''
    status:Optional[bool] =False

class ProductCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Name of the product category")
    parent: Optional[str] = Field(None, description="Name of the parent category")
    description: Optional[str] = Field(None, description="Description of the product category")
    status:Optional[bool] =False


class StatusUpdate(BaseModel):
    status: bool

class ProductSubCategoryCreate(BaseModel):
    prodcat_id: str
    prod_sub_name: str

class ProductSubCategoryUpdate(BaseModel):
    prod_sub_name: Optional[str] = None

class ProductCreate(BaseModel):
    prod_cat_id:str=''
    prod_sub_cat_id:str=''
    title: Optional[str] = ''
    description: Optional[str] = ''
    shortdescription:Optional[str] = ''
    actualprice: Optional[str] = ''
    sellingprice: Optional[str] = ''
    status: Optional[bool] = True
    skuid:Optional[str] = ''
    stockquantity:Optional[str] = ''
    linkedproductid: Optional[str]= ''

    # @validator('title', 'description')
    # def validate_title_and_description(cls, value):
    #     if not value:
    #         raise ValueError('Must not be empty')
    #     # Allow alphanumeric characters and spaces; adjust regex as needed
    #     if not all(char.isalnum() or char.isspace() for char in value):
    #         raise ValueError('Only alphanumeric characters and spaces are allowed')
    #     return value

    
class ProductUpdate(BaseModel):
    prod_cat_id: Optional[str] = None
    prod_sub_cat_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    shortdescription: Optional[str] = None
    actualprice: Optional[str] = None
    sellingprice: Optional[str] = None
    status: Optional[bool] = None
    skuid: Optional[str] = None
    stockquantity: Optional[str] = None