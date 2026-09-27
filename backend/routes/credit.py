import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import credit_service
from backend.services.credit_service import ValidationError

logger = logging.getLogger('vl_silks.credit')

credit_bp = Blueprint('credit', __name__)


def serialize_credit_profile(p):
    """Serialize credit profile dict for JSON output."""
    if not p:
        return None
    p_copy = dict(p)
    for key in ('credit_limit', 'total_credit_amount', 'total_paid_amount', 'outstanding_balance', 'available_credit'):
        if p_copy.get(key) is not None:
            p_copy[key] = float(p_copy[key])
    for dt_key in ('last_transaction_date', 'created_at', 'updated_at'):
        if p_copy.get(dt_key) is not None:
            p_copy[dt_key] = str(p_copy[dt_key])
    return p_copy


def serialize_ledger_item(item):
    """Serialize chronological credit ledger row for JSON output."""
    if not item:
        return None
    i_copy = dict(item)
    for key in ('amount', 'debit_amount', 'credit_amount', 'running_balance'):
        if i_copy.get(key) is not None:
            i_copy[key] = float(i_copy[key])
    for dt_key in ('transaction_date', 'created_at'):
        if i_copy.get(dt_key) is not None:
            i_copy[dt_key] = str(i_copy[dt_key])
    return i_copy


# =========================================================================
# WEB ROUTES
# =========================================================================

@credit_bp.route('/credit')
@login_required
def index():
    """
    Credit & Udhaar customer directory with summary metrics and search/filtering.
    Accessible to both Staff and Admin.
    """
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'ALL').strip()
    min_balance = request.args.get('min_balance', '').strip()

    customers = credit_service.get_credit_customers(
        search=search if search else None,
        status=status if status != 'ALL' else None,
        min_balance=min_balance if min_balance else None
    )

    summary = credit_service.get_credit_summary()

    return render_template(
        'credit/index.html',
        customers=customers,
        summary=summary,
        current_search=search,
        current_status=status,
        current_min_balance=min_balance
    )


@credit_bp.route('/credit/customer/<int:customer_id>')
@login_required
def view(customer_id):
    """
    View customer credit profile and full chronological Udhaar ledger.
    Accessible to both Staff and Admin.
    """
    profile = credit_service.get_customer_credit_profile(customer_id)
    if not profile:
        flash(f"Customer #{customer_id} was not found.", "warning")
        return redirect(url_for('credit.index'))

    ledger = credit_service.get_customer_credit_history(customer_id)

    return render_template(
        'credit/view.html',
        customer=profile,
        ledger=ledger
    )


@credit_bp.route('/credit/customer/<int:customer_id>/payment', methods=['GET', 'POST'])
@login_required
def payment(customer_id):
    """
    Record a settlement payment against outstanding Udhaar balance.
    Accessible to both Staff and Admin.
    """
    profile = credit_service.get_customer_credit_profile(customer_id)
    if not profile:
        flash(f"Customer #{customer_id} was not found.", "warning")
        return redirect(url_for('credit.index'))

    if profile['outstanding_balance'] <= 0:
        flash(f"Customer '{profile['customer_name']}' has no outstanding credit balance to settle.", "info")
        return redirect(url_for('credit.view', customer_id=customer_id))

    if request.method == 'POST':
        payment_data = {
            'amount': request.form.get('amount', '').strip(),
            'payment_method': request.form.get('payment_method', 'CASH').strip(),
            'payment_date': request.form.get('payment_date', '').strip() or date.today().strftime('%Y-%m-%d'),
            'reference_number': request.form.get('reference_number', '').strip() or None,
            'notes': request.form.get('notes', '').strip() or None,
        }

        user_id = session.get('user_id')
        try:
            result = credit_service.record_credit_payment(customer_id, payment_data, user_id)
            flash(
                f"Settlement payment of ₹{result['paid_amount']:,.2f} recorded successfully for {profile['customer_name']}! "
                f"New outstanding balance: ₹{result['new_balance']:,.2f}.",
                "success"
            )
            return redirect(url_for('credit.view', customer_id=customer_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('credit/payment.html', customer=profile, form_data=payment_data), 400
        except Exception as e:
            logger.error(f"Error recording credit payment: {e}")
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template('credit/payment.html', customer=profile, form_data=payment_data), 500

    default_form = {
        'amount': str(profile['outstanding_balance']),
        'payment_method': 'CASH',
        'payment_date': date.today().strftime('%Y-%m-%d'),
        'reference_number': '',
        'notes': ''
    }
    return render_template('credit/payment.html', customer=profile, form_data=default_form)


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@credit_bp.route('/api/credit/summary', methods=['GET'])
def api_get_credit_summary():
    """
    GET /api/credit/summary
    Retrieve high-level credit and Udhaar summary metrics.
    """
    summary = credit_service.get_credit_summary()
    return jsonify({
        "status": "success",
        "data": {
            "total_credit_customers": summary['total_credit_customers'],
            "total_credit_to_collect": float(summary['total_credit_to_collect']),
            "total_credit_sales_amount": float(summary['total_credit_sales_amount']),
            "total_settlements_amount": float(summary['total_settlements_amount']),
            "total_credit_sales_count": summary['total_credit_sales_count'],
            "total_settlements_count": summary['total_settlements_count']
        }
    }), 200


@credit_bp.route('/api/credit/customers', methods=['GET'])
def api_get_credit_customers():
    """
    GET /api/credit/customers
    Retrieve list of customers with outstanding Udhaar and query filters.
    """
    search = request.args.get('search', '').strip()
    status = request.args.get('status', '').strip()
    min_balance = request.args.get('min_balance', '').strip()

    customers = credit_service.get_credit_customers(
        search=search if search else None,
        status=status if status and status.upper() != 'ALL' else None,
        min_balance=min_balance if min_balance else None
    )

    serialized = []
    for c in customers:
        c_copy = dict(c)
        for key in ('credit_limit', 'outstanding_balance', 'available_credit'):
            if c_copy.get(key) is not None:
                c_copy[key] = float(c_copy[key])
        if c_copy.get('last_transaction_date'):
            c_copy['last_transaction_date'] = str(c_copy['last_transaction_date'])
        serialized.append(c_copy)

    return jsonify({
        "status": "success",
        "count": len(serialized),
        "data": serialized
    }), 200


@credit_bp.route('/api/credit/customer/<int:customer_id>', methods=['GET'])
def api_get_customer_credit_profile(customer_id):
    """
    GET /api/credit/customer/:id
    Retrieve detailed credit profile for a single customer.
    """
    profile = credit_service.get_customer_credit_profile(customer_id)
    if not profile:
        return jsonify({"status": "error", "message": f"Customer #{customer_id} not found"}), 404

    return jsonify({
        "status": "success",
        "data": serialize_credit_profile(profile)
    }), 200


@credit_bp.route('/api/credit/customer/<int:customer_id>/history', methods=['GET'])
def api_get_customer_credit_history(customer_id):
    """
    GET /api/credit/customer/:id/history
    Retrieve complete chronological credit transaction ledger for a customer.
    """
    profile = credit_service.get_customer_credit_profile(customer_id)
    if not profile:
        return jsonify({"status": "error", "message": f"Customer #{customer_id} not found"}), 404

    ledger = credit_service.get_customer_credit_history(customer_id)

    return jsonify({
        "status": "success",
        "customer_id": customer_id,
        "count": len(ledger),
        "ledger": [serialize_ledger_item(item) for item in ledger]
    }), 200


@credit_bp.route('/api/credit/customer/<int:customer_id>/payment', methods=['POST'])
def api_record_credit_payment(customer_id):
    """
    POST /api/credit/customer/:id/payment
    Record a settlement payment against a customer's outstanding Udhaar.
    """
    if 'user_id' not in session and not request.is_json:
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    data = request.get_json() or {}
    user_id = session.get('user_id') or data.get('user_id')
    if not user_id:
        return jsonify({"status": "error", "message": "Authenticated user ID is required"}), 401

    try:
        result = credit_service.record_credit_payment(customer_id, data, user_id)
        return jsonify({
            "status": "success",
            "message": f"Settlement payment of Rs.{result['paid_amount']} recorded successfully",
            "data": {
                "payment_id": result['payment_id'],
                "transaction_id": result['transaction_id'],
                "customer_id": result['customer_id'],
                "customer_name": result['customer_name'],
                "previous_balance": float(result['previous_balance']),
                "paid_amount": float(result['paid_amount']),
                "new_balance": float(result['new_balance'])
            }
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"API credit payment failed: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
