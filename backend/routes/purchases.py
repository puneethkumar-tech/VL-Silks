import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import purchase_service
from backend.services.purchase_service import ValidationError

logger = logging.getLogger('vl_silks.purchases')

purchases_bp = Blueprint('purchases', __name__)


# =========================================================================
# WEB ROUTES
# =========================================================================

@purchases_bp.route('/purchases')
@login_required
def index():
    """
    List all purchases with metrics summary, search, supplier, date, and status filters.
    """
    search = request.args.get('search', '').strip()
    supplier_id = request.args.get('supplier_id', '').strip()
    status = request.args.get('status', 'ALL').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    try:
        supplier_id_int = int(supplier_id) if supplier_id else None
    except ValueError:
        supplier_id_int = None

    purchases_list = purchase_service.get_all_purchases(
        search=search if search else None,
        supplier_id=supplier_id_int,
        status=status if status != 'ALL' else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None
    )

    metrics = purchase_service.get_purchase_summary_metrics()
    suppliers = purchase_service.get_active_suppliers()

    return render_template(
        'purchases/index.html',
        purchases=purchases_list,
        metrics=metrics,
        suppliers=suppliers,
        current_search=search,
        current_supplier_id=supplier_id,
        current_status=status,
        current_date_from=date_from,
        current_date_to=date_to
    )


@purchases_bp.route('/purchases/new', methods=['GET', 'POST'])
@admin_required
def new():
    """
    Create a new purchase / inward stock entry (Admin Only).
    """
    if request.method == 'POST':
        # Check if form data is sent or JSON
        if request.is_json:
            payload = request.get_json() or {}
            purchase_data = {
                'supplier_id': payload.get('supplier_id'),
                'invoice_number': payload.get('invoice_number'),
                'purchase_date': payload.get('purchase_date'),
                'payment_status': payload.get('payment_status', 'PAID'),
                'discount': payload.get('discount', 0.0),
                'tax': payload.get('tax', 0.0),
                'notes': payload.get('notes', '')
            }
            items_data = payload.get('items', [])
        else:
            purchase_data = {
                'supplier_id': request.form.get('supplier_id'),
                'invoice_number': request.form.get('invoice_number', '').strip(),
                'purchase_date': request.form.get('purchase_date', '').strip(),
                'payment_status': request.form.get('payment_status', 'PAID').strip(),
                'discount': request.form.get('discount', '0.00').strip(),
                'tax': request.form.get('tax', '0.00').strip(),
                'notes': request.form.get('notes', '').strip()
            }

            variant_ids = request.form.getlist('variant_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')

            items_data = []
            for v_id, qty, price in zip(variant_ids, quantities, unit_prices):
                if v_id and str(v_id).strip():
                    items_data.append({
                        'variant_id': v_id,
                        'quantity': qty,
                        'unit_price': price
                    })

        user_id = session.get('user_id')
        try:
            purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id)
            flash(f"Purchase invoice '{purchase_data.get('invoice_number')}' created successfully! Stock updated.", "success")
            if request.is_json:
                return jsonify({
                    'message': 'Purchase created successfully',
                    'purchase_id': purchase_id,
                    'invoice_number': purchase_data.get('invoice_number')
                }), 201
            return redirect(url_for('purchases.view', purchase_id=purchase_id))

        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            if request.is_json:
                return jsonify({'error': 'Validation Error', 'message': str(e)}), 400
            # Reload page with form data
            suppliers = purchase_service.get_active_suppliers()
            variants = purchase_service.get_active_variants()
            return render_template(
                'purchases/new.html',
                suppliers=suppliers,
                variants=variants,
                form_data=purchase_data,
                items_data=items_data,
                today_date=date.today().strftime('%Y-%m-%d')
            ), 400

        except Exception as e:
            logger.error(f"Unexpected error creating purchase: {e}")
            flash(f"System Error: Unable to record purchase. Please try again.", "danger")
            if request.is_json:
                return jsonify({'error': 'Internal Error', 'message': str(e)}), 500
            suppliers = purchase_service.get_active_suppliers()
            variants = purchase_service.get_active_variants()
            return render_template(
                'purchases/new.html',
                suppliers=suppliers,
                variants=variants,
                form_data=purchase_data,
                items_data=items_data,
                today_date=date.today().strftime('%Y-%m-%d')
            ), 500

    # GET request
    suppliers = purchase_service.get_active_suppliers()
    variants = purchase_service.get_active_variants()
    return render_template(
        'purchases/new.html',
        suppliers=suppliers,
        variants=variants,
        form_data={},
        items_data=[],
        today_date=date.today().strftime('%Y-%m-%d')
    )


@purchases_bp.route('/purchases/<int:purchase_id>')
@login_required
def view(purchase_id):
    """
    View complete purchase details, line items, and stock movement impact.
    """
    purchase = purchase_service.get_purchase_by_id(purchase_id)
    if not purchase:
        flash(f"Purchase with ID #{purchase_id} was not found.", "warning")
        return redirect(url_for('purchases.index'))

    items = purchase_service.get_purchase_items(purchase_id)
    return render_template(
        'purchases/view.html',
        purchase=purchase,
        items=items
    )


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@purchases_bp.route('/api/purchases', methods=['GET'])
def api_list_purchases():
    """
    GET /api/purchases
    Retrieve purchases list as JSON with optional filtering.
    """
    search = request.args.get('search', '').strip()
    supplier_id = request.args.get('supplier_id', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    try:
        supplier_id_int = int(supplier_id) if supplier_id else None
    except ValueError:
        supplier_id_int = None

    purchases = purchase_service.get_all_purchases(
        search=search if search else None,
        supplier_id=supplier_id_int,
        status=status if status and status.upper() != 'ALL' else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None
    )

    # Convert Decimal/date objects for JSON serialization
    serialized = []
    for p in purchases:
        p_copy = dict(p)
        for key in ('subtotal', 'discount', 'tax', 'total'):
            if p_copy.get(key) is not None:
                p_copy[key] = float(p_copy[key])
        if p_copy.get('purchase_date'):
            p_copy['purchase_date'] = str(p_copy['purchase_date'])
        if p_copy.get('created_at'):
            p_copy['created_at'] = str(p_copy['created_at'])
        serialized.append(p_copy)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'purchases': serialized
    }), 200


@purchases_bp.route('/api/purchases/<int:purchase_id>', methods=['GET'])
def api_get_purchase(purchase_id):
    """
    GET /api/purchases/<purchase_id>
    Retrieve single purchase record with line items as JSON.
    """
    purchase = purchase_service.get_purchase_by_id(purchase_id)
    if not purchase:
        return jsonify({
            'status': 'error',
            'message': f"Purchase #{purchase_id} not found"
        }), 404

    items = purchase_service.get_purchase_items(purchase_id)

    purchase_dict = dict(purchase)
    for key in ('subtotal', 'discount', 'tax', 'total'):
        if purchase_dict.get(key) is not None:
            purchase_dict[key] = float(purchase_dict[key])
    if purchase_dict.get('purchase_date'):
        purchase_dict['purchase_date'] = str(purchase_dict['purchase_date'])
    if purchase_dict.get('created_at'):
        purchase_dict['created_at'] = str(purchase_dict['created_at'])
    if purchase_dict.get('updated_at'):
        purchase_dict['updated_at'] = str(purchase_dict['updated_at'])

    items_list = []
    for it in items:
        it_dict = dict(it)
        for key in ('unit_price', 'total_price', 'selling_price'):
            if it_dict.get(key) is not None:
                it_dict[key] = float(it_dict[key])
        if it_dict.get('created_at'):
            it_dict['created_at'] = str(it_dict['created_at'])
        items_list.append(it_dict)

    purchase_dict['items'] = items_list
    return jsonify({
        'status': 'success',
        'purchase': purchase_dict
    }), 200


@purchases_bp.route('/api/purchases', methods=['POST'])
def api_create_purchase():
    """
    POST /api/purchases
    Atomically create a purchase with line items via REST API (Admin Only).
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({'status': 'error', 'message': 'Admin authorization required'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'JSON request body is required'}), 400

    purchase_data = {
        'supplier_id': data.get('supplier_id'),
        'invoice_number': data.get('invoice_number'),
        'purchase_date': data.get('purchase_date'),
        'payment_status': data.get('payment_status', 'PAID'),
        'discount': data.get('discount', 0.0),
        'tax': data.get('tax', 0.0),
        'notes': data.get('notes', '')
    }
    items_data = data.get('items', [])

    user_id = session.get('user_id') or data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Authenticated user ID is required'}), 401

    try:
        purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id)
        created_purchase = purchase_service.get_purchase_by_id(purchase_id)
        return jsonify({
            'status': 'success',
            'message': 'Purchase created successfully and stock updated',
            'purchase_id': purchase_id,
            'invoice_number': purchase_data.get('invoice_number'),
            'total': float(created_purchase['total']) if created_purchase else 0.0
        }), 201
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"API purchase creation failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
