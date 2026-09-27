import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import sale_service
from backend.services.sale_service import ValidationError

logger = logging.getLogger('vl_silks.sales')

sales_bp = Blueprint('sales', __name__)


# =========================================================================
# WEB ROUTES
# =========================================================================

@sales_bp.route('/sales')
@login_required
def index():
    """
    List all sales with metrics summary, search, and filter options.
    """
    search = request.args.get('search', '').strip()
    payment_method = request.args.get('payment_method', 'ALL').strip()
    payment_status = request.args.get('payment_status', 'ALL').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    sales_list = sale_service.get_all_sales(
        search=search if search else None,
        payment_method=payment_method if payment_method != 'ALL' else None,
        payment_status=payment_status if payment_status != 'ALL' else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
    )

    metrics = sale_service.get_sale_summary_metrics()

    return render_template(
        'sales/index.html',
        sales=sales_list,
        metrics=metrics,
        current_search=search,
        current_payment_method=payment_method,
        current_payment_status=payment_status,
        current_date_from=date_from,
        current_date_to=date_to,
    )


@sales_bp.route('/sales/new', methods=['GET', 'POST'])
@login_required
def new():
    """
    POS — Create a new sale / billing invoice.
    Accessible by both ADMIN and STAFF.
    """
    if request.method == 'POST':
        if request.is_json:
            payload = request.get_json() or {}
            sale_data = {
                'customer_id': payload.get('customer_id'),
                'sale_date': payload.get('sale_date'),
                'payment_method': payload.get('payment_method', 'CASH'),
                'paid_amount': payload.get('paid_amount'),
                'discount': payload.get('discount', 0.0),
                'tax': payload.get('tax', 0.0),
                'notes': payload.get('notes', ''),
                'invoice_number': payload.get('invoice_number', ''),
            }
            items_data = payload.get('items', [])
        else:
            sale_data = {
                'customer_id': request.form.get('customer_id', '').strip() or None,
                'sale_date': request.form.get('sale_date', '').strip(),
                'payment_method': request.form.get('payment_method', 'CASH').strip(),
                'paid_amount': request.form.get('paid_amount', '').strip() or None,
                'discount': request.form.get('discount', '0.00').strip(),
                'tax': request.form.get('tax', '0.00').strip(),
                'notes': request.form.get('notes', '').strip(),
                'invoice_number': request.form.get('invoice_number', '').strip(),
            }

            variant_ids = request.form.getlist('variant_id[]')
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            item_discounts = request.form.getlist('item_discount[]')

            items_data = []
            for v_id, qty, price, idiscount in zip(
                variant_ids, quantities, unit_prices, item_discounts or ['0.00'] * len(variant_ids)
            ):
                if v_id and str(v_id).strip():
                    items_data.append({
                        'variant_id': v_id,
                        'quantity': qty,
                        'unit_price': price,
                        'item_discount': idiscount or '0.00',
                    })

        user_id = session.get('user_id')
        try:
            sale_id = sale_service.create_sale(sale_data, items_data, user_id)
            invoice_num = sale_data.get('invoice_number') or ''
            flash(
                f"Sale invoice '{invoice_num or '#' + str(sale_id)}' created successfully! Stock updated.",
                "success"
            )
            if request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': 'Sale created successfully',
                    'sale_id': sale_id,
                }), 201
            return redirect(url_for('sales.view', sale_id=sale_id))

        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            if request.is_json:
                return jsonify({'status': 'error', 'error': 'Validation Error', 'message': str(e)}), 400
            variants = sale_service.get_active_variants_for_sale()
            customers = sale_service.get_active_customers()
            return render_template(
                'sales/new.html',
                variants=variants,
                customers=customers,
                form_data=sale_data,
                items_data=items_data,
                today_date=date.today().strftime('%Y-%m-%d'),
            ), 400

        except Exception as e:
            logger.error(f"Unexpected error creating sale: {e}")
            flash("System Error: Unable to record sale. Please try again.", "danger")
            if request.is_json:
                return jsonify({'status': 'error', 'message': str(e)}), 500
            variants = sale_service.get_active_variants_for_sale()
            customers = sale_service.get_active_customers()
            return render_template(
                'sales/new.html',
                variants=variants,
                customers=customers,
                form_data=sale_data,
                items_data=items_data,
                today_date=date.today().strftime('%Y-%m-%d'),
            ), 500

    # GET request
    variants = sale_service.get_active_variants_for_sale()
    customers = sale_service.get_active_customers()
    return render_template(
        'sales/new.html',
        variants=variants,
        customers=customers,
        form_data={},
        items_data=[],
        today_date=date.today().strftime('%Y-%m-%d'),
    )


@sales_bp.route('/sales/<int:sale_id>')
@login_required
def view(sale_id):
    """
    View complete sale / invoice details and line items.
    """
    sale = sale_service.get_sale_by_id(sale_id)
    if not sale:
        flash(f"Sale with ID #{sale_id} was not found.", "warning")
        return redirect(url_for('sales.index'))

    items = sale_service.get_sale_items(sale_id)
    return render_template(
        'sales/view.html',
        sale=sale,
        items=items,
    )


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@sales_bp.route('/api/sales', methods=['GET'])
def api_list_sales():
    """
    GET /api/sales
    Retrieve sales list as JSON with optional filtering.
    """
    search = request.args.get('search', '').strip()
    payment_method = request.args.get('payment_method', '').strip()
    payment_status = request.args.get('payment_status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    sales = sale_service.get_all_sales(
        search=search if search else None,
        payment_method=payment_method if payment_method and payment_method.upper() != 'ALL' else None,
        payment_status=payment_status if payment_status and payment_status.upper() != 'ALL' else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
    )

    serialized = []
    for s in sales:
        s_copy = dict(s)
        for key in ('subtotal', 'discount', 'tax', 'total_amount', 'paid_amount', 'balance_amount'):
            if s_copy.get(key) is not None:
                s_copy[key] = float(s_copy[key])
        if s_copy.get('sale_date'):
            s_copy['sale_date'] = str(s_copy['sale_date'])
        if s_copy.get('created_at'):
            s_copy['created_at'] = str(s_copy['created_at'])
        serialized.append(s_copy)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'sales': serialized,
    }), 200


@sales_bp.route('/api/sales/<int:sale_id>', methods=['GET'])
def api_get_sale(sale_id):
    """
    GET /api/sales/<sale_id>
    Retrieve single sale record with line items as JSON.
    """
    sale = sale_service.get_sale_by_id(sale_id)
    if not sale:
        return jsonify({'status': 'error', 'message': f"Sale #{sale_id} not found"}), 404

    items = sale_service.get_sale_items(sale_id)

    sale_dict = dict(sale)
    for key in ('subtotal', 'discount', 'tax', 'total_amount', 'paid_amount', 'balance_amount', 'credit_limit'):
        if sale_dict.get(key) is not None:
            sale_dict[key] = float(sale_dict[key])
    for dt_key in ('sale_date', 'created_at', 'updated_at'):
        if sale_dict.get(dt_key):
            sale_dict[dt_key] = str(sale_dict[dt_key])

    items_list = []
    for it in items:
        it_dict = dict(it)
        for key in ('unit_price', 'discount', 'total_price'):
            if it_dict.get(key) is not None:
                it_dict[key] = float(it_dict[key])
        if it_dict.get('created_at'):
            it_dict['created_at'] = str(it_dict['created_at'])
        items_list.append(it_dict)

    sale_dict['items'] = items_list
    return jsonify({
        'status': 'success',
        'sale': sale_dict,
        'items': items_list
    }), 200


@sales_bp.route('/api/sales', methods=['POST'])
def api_create_sale():
    """
    POST /api/sales
    Atomically create a sale with line items via REST API.
    """
    if 'user_id' not in session and not request.is_json:
        return jsonify({'status': 'error', 'message': 'Authentication required'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'JSON request body is required'}), 400

    sale_data = {
        'customer_id': data.get('customer_id'),
        'sale_date': data.get('sale_date'),
        'payment_method': data.get('payment_method', 'CASH'),
        'paid_amount': data.get('paid_amount'),
        'discount': data.get('discount', 0.0),
        'tax': data.get('tax', 0.0),
        'notes': data.get('notes', ''),
        'invoice_number': data.get('invoice_number', ''),
    }
    items_data = data.get('items', [])

    user_id = session.get('user_id') or data.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Authenticated user ID is required'}), 401

    try:
        sale_id = sale_service.create_sale(sale_data, items_data, user_id)
        created_sale = sale_service.get_sale_by_id(sale_id)
        return jsonify({
            'status': 'success',
            'message': 'Sale created successfully and stock updated',
            'sale_id': sale_id,
            'invoice_number': created_sale['invoice_number'] if created_sale else '',
            'total_amount': float(created_sale['total_amount']) if created_sale else 0.0,
            'payment_status': created_sale['payment_status'] if created_sale else '',
        }), 201
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"API sale creation failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@sales_bp.route('/api/pos/variants/search', methods=['GET'])
def api_pos_search_variants():
    """
    GET /api/pos/variants/search?q=query
    Search active product variants for the POS interface.
    """
    query = request.args.get('q', '').strip()
    variants = sale_service.get_active_variants_for_sale(search=query if query else None)

    serialized = []
    for v in variants:
        v_dict = dict(v)
        if v_dict.get('selling_price') is not None:
            v_dict['selling_price'] = float(v_dict['selling_price'])
        serialized.append(v_dict)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'variants': serialized
    }), 200


@sales_bp.route('/api/pos/customers/search', methods=['GET'])
def api_pos_search_customers():
    """
    GET /api/pos/customers/search?q=query
    Search active customers with current balance and credit limits for POS checkout.
    """
    query = request.args.get('q', '').strip()
    customers = sale_service.get_active_customers(search=query if query else None)

    serialized = []
    for c in customers:
        c_dict = dict(c)
        for key in ('credit_limit', 'current_balance', 'available_credit'):
            if c_dict.get(key) is not None:
                c_dict[key] = float(c_dict[key])
        serialized.append(c_dict)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'customers': serialized
    }), 200


@sales_bp.route('/api/pos/customers/quick-create', methods=['POST'])
def api_pos_quick_create_customer():
    """
    POST /api/pos/customers/quick-create
    Quickly register a new customer from the POS checkout modal.
    """
    data = request.get_json() or {}
    name = data.get('customer_name', '').strip()
    phone = data.get('phone', '').strip()
    limit = data.get('credit_limit', 25000.0)
    email = data.get('email', '').strip() or None
    address = data.get('address', '').strip() or None

    try:
        cust_id = sale_service.quick_create_customer(
            customer_name=name,
            phone=phone,
            credit_limit=limit,
            email=email,
            address=address
        )
        return jsonify({
            'status': 'success',
            'message': f"Customer '{name}' registered successfully.",
            'customer_id': cust_id,
            'customer_name': name,
            'phone': phone,
            'credit_limit': float(limit) if limit else 25000.0,
            'current_balance': 0.0,
            'available_credit': float(limit) if limit else 25000.0
        }), 201
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in quick creating customer: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

