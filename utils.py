# utils.py
from passlib.hash import bcrypt
from dotenv import load_dotenv
import random
import string
from sqlalchemy import event
from datetime import datetime, timezone
from passlib.context import CryptContext

from database import SessionLocal

# Load environment variables from .env file
load_dotenv("credentials.env")

def hash_password(password: str) -> str:
    return bcrypt.hash(password)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define the validate_password function
def validate_password(Id_password: str):
        if 8 <= len(Id_password) <= 16:
            if any(c.islower() for c in Id_password) and \
                any(c.isupper() for c in Id_password) and \
                any(c.isdigit() for c in Id_password) and \
                any(c in '!@#$%^&*()-_=+[]{}|;:,.<>?/~`' for c in Id_password):
                return {"status_code": 200, "message": "Password is valid."}
            return {"status_code": 400, "message": "Password must contain atleast one Uppercase, one Lowercase, one Digit, one Special Character."}
        return {"status_code": 400, "message": "Password length must be between 8 and 12 characters."}
    
def generate_random_token():
    characters = string.ascii_lowercase 
    return ''.join(random.choice(characters) for _ in range(6))

def random_token():
    # Generate random hexadecimal digits for each part of the UUID
    parts = [
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(8)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(4)),
        ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))
    ]
    
    # Combine the parts with hyphens in the specified format
    authtoken = '-'.join(parts)
    return authtoken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Verify password function
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# # Event listener to set Days180Flag
# def calculate_id_user_days180flag(mapper, connection, target):
#     if target.tstamp is not None:
#         current_time = datetime.now(timezone.utc)
#         delta = current_time - target.tstamp
#         days180 = 180
#         target.Days180Flag = int(delta.days >= days180)

# # Attach the event listener to the UserLogin class
# event.listen(UserLogin, 'before_insert', calculate_id_user_days180flag)
# event.listen(UserLogin, 'before_update', calculate_id_user_days180flag)

