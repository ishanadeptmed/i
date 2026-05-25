import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
RAW_FOLDER = os.path.join(UPLOAD_FOLDER, "raw")
CLEAN_FOLDER = os.path.join(UPLOAD_FOLDER, "clean")
PROCESSED_FOLDER = os.path.join(UPLOAD_FOLDER, "processed")

# Stable raw filenames per month folder
RAW_ACTIVATION_NAME = "ActivationDetailReport.csv"
RAW_CUR_CALLIDUS_NAME = "curCallidus.csv"
RAW_CALLIDUS_DETAIL_NAME = "CallidusDetail.csv"

PROCESSED_MERGED_NAME = "merged_activations.csv"
PROCESSED_SUMMARY_NAME = "summary.json"
PROCESSED_MANIFEST_NAME = "manifest.json"

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
