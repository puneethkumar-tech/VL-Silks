from flask import Blueprint, jsonify
from backend.utils.database import query_db

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    Returns:
        JSON status response.
    """
    db_status = "connected"
    try:
        query_db("SELECT 1 AS test", one=True)
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "ok",
        "service": "VL Silks",
        "database": db_status
    }), 200
