import os
from flask import Flask, redirect, url_for
from routes.upload_routes import upload_bp
from routes.processing_routes import processing_bp
from routes.dashboard_routes import dashboard_bp
from config import (
    UPLOAD_FOLDER,
    RAW_FOLDER,
    CLEAN_FOLDER,
    SECRET_KEY,
    DEBUG,
    MAX_CONTENT_LENGTH
)

app = Flask(__name__)

# =========================================================
# APP CONFIG
# =========================================================

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RAW_FOLDER"] = RAW_FOLDER
app.config["CLEAN_FOLDER"] = CLEAN_FOLDER
app.config["SECRET_KEY"] = SECRET_KEY
app.config["DEBUG"] = DEBUG
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

# =========================================================
# CREATE REQUIRED DIRECTORIES
# =========================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RAW_FOLDER, exist_ok=True)
os.makedirs(CLEAN_FOLDER, exist_ok=True)

# =========================================================
# REGISTER BLUEPRINTS
# =========================================================

# Upload Pages / APIs
app.register_blueprint(upload_bp)

# Pandas Cleaning + Processing
app.register_blueprint(processing_bp)

# Dashboard / Preview Routes
app.register_blueprint(dashboard_bp)

# =========================================================
# HOME ROUTE
# =========================================================

@app.route("/")
def home():
    """
    Redirect user to upload page
    """
    return redirect(url_for("upload.upload_page"))

# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():
    return {
        "status": "running",
        "message": "CSV/Excel Processing App Running"
    }, 200

# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def file_too_large(error):
    return {
        "error": "File too large"
    }, 413


@app.errorhandler(404)
def page_not_found(error):
    return {
        "error": "Page not found"
    }, 404


@app.errorhandler(500)
def internal_error(error):
    return {
        "error": "Internal server error"
    }, 500

# =========================================================
# RUN APP
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )