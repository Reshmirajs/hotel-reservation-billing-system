import os
from dotenv import load_dotenv

# Load local .env file if it exists (ignored in Vercel production)
load_dotenv()

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "i@mReshm1")
MYSQL_DB = os.environ.get("MYSQL_DB", "hotel_db")