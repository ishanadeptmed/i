import os
import pandas as pd

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    current_app
)

from werkzeug.utils import secure_filename

# =========================================================
# BLUEPRINT
# =========================================================

upload_bp = Blueprint("upload", __name__)

# =========================================================
# ALLOWED FILE TYPES
# =========================================================

ALLOWED_EXTENSIONS = {"csv", "xlsx"}

# =========================================================
# HELPERS
# =========================================================

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# =========================================================
# UPLOAD PAGE
# =========================================================

@upload_bp.route("/")
def upload_page():
    return render_template("upload.html")

# =========================================================
# FILE UPLOAD
# =========================================================

@upload_bp.route("/upload", methods=["POST"])
def upload_files():

    if "file1" not in request.files:
        return jsonify({
            "error": "File1 missing"
        }), 400

    if "file2" not in request.files:
        return jsonify({
            "error": "File2 missing"
        }), 400

    file1 = request.files["file1"]
    file2 = request.files["file2"]

    # Validate names
    if file1.filename == "":
        return jsonify({"error": "File1 empty"}), 400

    if file2.filename == "":
        return jsonify({"error": "File2 empty"}), 400

    # Validate extensions
    if not allowed_file(file1.filename):
        return jsonify({
            "error": "Invalid File1 type"
        }), 400

    if not allowed_file(file2.filename):
        return jsonify({
            "error": "Invalid File2 type"
        }), 400

    # Secure names
    filename1 = secure_filename(file1.filename)
    filename2 = secure_filename(file2.filename)

    raw_folder = current_app.config["RAW_FOLDER"]

    filepath1 = os.path.join(raw_folder, filename1)
    filepath2 = os.path.join(raw_folder, filename2)

    # Save raw files
    file1.save(filepath1)
    file2.save(filepath2)

    # Read preview
    try:

        if filename1.endswith(".csv"):
            df1 = pd.read_csv(filepath1)
        else:
            df1 = pd.read_excel(filepath1)

        if filename2.endswith(".csv"):
            df2 = pd.read_csv(filepath2)
        else:
            df2 = pd.read_excel(filepath2)

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

    return jsonify({
        "message": "Files uploaded successfully",
        "file1_rows": len(df1),
        "file2_rows": len(df2),
        "file1_columns": list(df1.columns),
        "file2_columns": list(df2.columns)
    })