import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(filename='logger.log', level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv("credentials.env")

# Load the private key
with open("keyfiles/private.pem", "rb") as key_file:
    PRIVATE_KEY = key_file.read()

# Load the public key
with open("keyfiles/public.pem", "rb") as key_file:
    PUBLIC_KEY = key_file.read()
    

DATABASE_URL = os.getenv('DATABASE_URL')
UPLOAD_DIR = ""

# Log an info message
logger.info("This is an info message")
