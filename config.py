import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RAW_FOLDER = os.path.join(UPLOAD_FOLDER, "raw")
CLEAN_FOLDER = os.path.join(UPLOAD_FOLDER, "clean")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

DEBUG = True

# 100 MB upload limit
MAX_CONTENT_LENGTH = 100 * 1024 * 1024