from flask import Blueprint, jsonify

# =========================================================
# BLUEPRINT
# =========================================================

dashboard_bp = Blueprint(
    "dashboard",
    __name__
)

# =========================================================
# DASHBOARD ROUTE
# =========================================================

@dashboard_bp.route("/dashboard")
def dashboard():

    return jsonify({
        "message": "Dashboard route working"
    })