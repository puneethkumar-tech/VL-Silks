"""
VL Silks – PDF Routes Blueprint
Handles PDF statement generation and download endpoints for Credit/Udhaar, Invoices, and Reports.
"""

import io
import logging
from flask import Blueprint, request, make_response, jsonify, session, send_file, flash, redirect, url_for
from backend.routes.auth import login_required
from backend.services import pdf_service
from backend.services.credit_service import ValidationError

logger = logging.getLogger('vl_silks.pdf')

pdf_bp = Blueprint('pdf', __name__)


@pdf_bp.route('/api/pdf/credit/<int:customer_id>', methods=['GET'])
def api_download_credit_statement(customer_id):
    """
    GET /api/pdf/credit/:customer_id
    Generate and stream branded Credit / Udhaar Statement PDF.
    
    Query Parameters:
      - date_from (optional, YYYY-MM-DD)
      - date_to (optional, YYYY-MM-DD)
      
    Response:
      - 200 OK with application/pdf binary stream
      - 400 Bad Request on invalid date parameters
      - 401 Unauthorized if not authenticated
      - 404 Not Found if customer does not exist
      - 500 Internal Server Error on unexpected generation failure
    """
    # 1. Authentication Check (Accepts either active session or authenticated header)
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Authentication required to download statements"}), 401

    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None

    try:
        pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to
        )

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    except LookupError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to generate credit statement PDF for customer {customer_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"PDF Generation Error: {str(e)}"}), 500


@pdf_bp.route('/credit/customer/<int:customer_id>/statement', methods=['GET'])
@login_required
def web_download_credit_statement(customer_id):
    """
    Web direct download action for customer credit statement.
    Supports query parameters for statement period filtering.
    """
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None

    try:
        pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to
        )

        response = make_response(pdf_bytes)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except LookupError as e:
        flash(str(e), "warning")
        return redirect(url_for('credit.index'))
    except ValidationError as e:
        flash(f"Invalid statement period: {str(e)}", "danger")
        return redirect(url_for('credit.view', customer_id=customer_id))
    except Exception as e:
        logger.error(f"Web PDF statement generation error: {e}", exc_info=True)
        flash("An unexpected error occurred while generating the PDF statement.", "danger")
        return redirect(url_for('credit.view', customer_id=customer_id))
