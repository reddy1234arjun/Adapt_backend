from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.user_models import Base as UserBase
from models.product_models import Base as ProductBaseModel
from config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables for both bases
UserBase.metadata.create_all(bind=engine)
ProductBaseModel.metadata.create_all(bind=engine)
