import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import customer_service
from backend.services.customer_service import ValidationError

logger = logging.getLogger('vl_silks.customers')

customers_bp = Blueprint('customers', __name__)


def serialize_customer(cust):
    """Convert Decimal and datetime objects in customer dict for JSON response."""
    if not cust:
        return None
    c_copy = dict(cust)
    for key in ('credit_limit', 'total_purchase_value', 'total_paid',
                'outstanding_balance', 'available_credit', 'current_balance'):
        if c_copy.get(key) is not None:
            c_copy[key] = float(c_copy[key])
    for dt_key in ('created_at', 'updated_at'):
        if c_copy.get(dt_key) is not None:
            c_copy[dt_key] = str(c_copy[dt_key])
    return c_copy


def serialize_purchase(p):
    """Convert Decimal and datetime objects in purchase dict for JSON response."""
    if not p:
        return None
    p_copy = dict(p)
    for key in ('subtotal', 'discount', 'tax', 'total_amount', 'paid_amount', 'balance_amount'):
        if p_copy.get(key) is not None:
            p_copy[key] = float(p_copy[key])
    for dt_key in ('sale_date', 'created_at', 'updated_at'):
        if p_copy.get(dt_key) is not None:
            p_copy[dt_key] = str(p_copy[dt_key])
    return p_copy


# =========================================================================
# WEB ROUTES
# =========================================================================

@customers_bp.route('/customers')
@login_required
def index():
    """
    List all customers with purchase summary metrics, search, and status filter.
    Accessible to both ADMIN and STAFF.
    """
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'ALL').strip()

    customers_list = customer_service.get_customers(
        search=search if search else None,
        status=status if status != 'ALL' else None
    )

    metrics = customer_service.get_customer_summary_metrics()

    return render_template(
        'customers/index.html',
        customers=customers_list,
        metrics=metrics,
        current_search=search,
        current_status=status
    )


@customers_bp.route('/customers/new', methods=['GET', 'POST'])
@admin_required
def new():
    """
    Add a new customer (Admin Only).
    """
    if request.method == 'POST':
        customer_data = {
            'customer_name': request.form.get('customer_name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip() or None,
            'address': request.form.get('address', '').strip() or None,
            'credit_limit': request.form.get('credit_limit', '25000.00').strip(),
            'status': request.form.get('status', 'ACTIVE').strip()
        }

        try:
            customer_id = customer_service.create_customer(customer_data)
            flash(f"Customer '{customer_data['customer_name']}' registered successfully!", "success")
            return redirect(url_for('customers.view', customer_id=customer_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('customers/new.html', form_data=customer_data), 400
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template('customers/new.html', form_data=customer_data), 500

    return render_template('customers/new.html', form_data={'credit_limit': '25000.00', 'status': 'ACTIVE'})


@customers_bp.route('/customers/<int:customer_id>')
@login_required
def view(customer_id):
    """
    View customer profile with purchase statistics and recent purchase history.
    Accessible to both ADMIN and STAFF.
    """
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash(f"Customer #{customer_id} not found.", "warning")
        return redirect(url_for('customers.index'))

    purchases = customer_service.get_customer_purchase_history(customer_id)

    return render_template(
        'customers/view.html',
        customer=customer,
        purchases=purchases
    )


@customers_bp.route('/customers/<int:customer_id>/purchases')
@login_required
def purchases(customer_id):
    """
    Dedicated view for a customer's complete purchase history.
    """
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash(f"Customer #{customer_id} not found.", "warning")
        return redirect(url_for('customers.index'))

    purchases_list = customer_service.get_customer_purchase_history(customer_id)

    return render_template(
        'customers/purchases.html',
        customer=customer,
        purchases=purchases_list
    )


@customers_bp.route('/customers/<int:customer_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(customer_id):
    """
    Edit an existing customer's details (Admin Only).
    """
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        flash(f"Customer #{customer_id} not found.", "warning")
        return redirect(url_for('customers.index'))

    if request.method == 'POST':
        customer_data = {
            'customer_name': request.form.get('customer_name', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip() or None,
            'address': request.form.get('address', '').strip() or None,
            'credit_limit': request.form.get('credit_limit', str(customer['credit_limit'])).strip(),
            'status': request.form.get('status', customer['status']).strip()
        }

        try:
            customer_service.update_customer(customer_id, customer_data)
            flash(f"Customer '{customer_data['customer_name']}' updated successfully!", "success")
            return redirect(url_for('customers.view', customer_id=customer_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('customers/edit.html', customer=customer, form_data=customer_data), 400
        except Exception as e:
            logger.error(f"Error updating customer #{customer_id}: {e}")
            flash(f"Error updating customer: {str(e)}", "danger")
            return render_template('customers/edit.html', customer=customer, form_data=customer_data), 500

    return render_template('customers/edit.html', customer=customer, form_data=customer)


@customers_bp.route('/customers/<int:customer_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(customer_id):
    """
    Safely toggle active/inactive status of a customer (Admin Only).
    Preserves all historical sales and credit transactions.
    """
    try:
        new_status = customer_service.toggle_customer_status(customer_id)
        flash(f"Customer status updated to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update customer status: {str(e)}", "danger")
    return redirect(request.referrer or url_for('customers.view', customer_id=customer_id))


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@customers_bp.route('/api/customers', methods=['GET'])
def api_get_customers():
    """
    GET /api/customers
    List customers with optional search, phone, and status filters.
    """
    search = request.args.get('search', '').strip()
    phone = request.args.get('phone', '').strip()
    status = request.args.get('status', '').strip()

    search_query = phone if phone else (search if search else None)
    status_filter = status if status and status.upper() != 'ALL' else None

    customers_list = customer_service.get_customers(
        search=search_query,
        status=status_filter
    )

    serialized = [serialize_customer(c) for c in customers_list]

    return jsonify({
        "status": "success",
        "count": len(serialized),
        "data": serialized
    }), 200


@customers_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
def api_get_customer(customer_id):
    """
    GET /api/customers/:id
    Single customer details with purchase summary and recent purchases.
    """
    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({"status": "error", "message": f"Customer #{customer_id} not found"}), 404

    purchases = customer_service.get_customer_purchase_history(customer_id)

    return jsonify({
        "status": "success",
        "data": serialize_customer(customer),
        "purchases": [serialize_purchase(p) for p in purchases]
    }), 200


@customers_bp.route('/api/customers', methods=['POST'])
def api_create_customer():
    """
    POST /api/customers
    Create a new customer via REST API. (Admin Only)
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    try:
        customer_id = customer_service.create_customer(data)
        created = customer_service.get_customer_by_id(customer_id)
        return jsonify({
            "status": "success",
            "message": "Customer created successfully",
            "customer_id": customer_id,
            "data": serialize_customer(created)
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"API customer creation failed: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@customers_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
def api_update_customer(customer_id):
    """
    PUT /api/customers/:id
    Update an existing customer (Admin Only).
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    customer = customer_service.get_customer_by_id(customer_id)
    if not customer:
        return jsonify({"status": "error", "message": f"Customer #{customer_id} not found"}), 404

    data = request.get_json() or {}
    try:
        customer_service.update_customer(customer_id, data)
        updated = customer_service.get_customer_by_id(customer_id)
        return jsonify({
            "status": "success",
            "message": "Customer updated successfully",
            "data": serialize_customer(updated)
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"API customer update failed: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@customers_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
def api_delete_customer(customer_id):
    """
    DELETE /api/customers/:id
    Safe deactivation of customer (Admin Only).
    Preserves all historical sales and credit records.
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        customer_service.delete_customer(customer_id)
        return jsonify({
            "status": "success",
            "message": f"Customer #{customer_id} safely deactivated. Historical records preserved."
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        logger.error(f"API customer deletion failed: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
