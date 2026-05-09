from flask import Blueprint, jsonify

# =========================================================
# BLUEPRINT
# =========================================================

processing_bp = Blueprint(
    "processing",
    __name__
)

# =========================================================
# TEST ROUTE
# =========================================================

@processing_bp.route("/process")
def process_data():

    return jsonify({
        "message": "Processing route working"
    })