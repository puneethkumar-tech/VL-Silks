"""
VL Silks – Returns & Exchanges Routes Blueprint
Provides Web routes and REST API endpoints for return processing, condition inspection,
and garment exchange workflows.
"""

import logging
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import return_service, sale_service, product_service
from backend.services.return_service import ValidationError

logger = logging.getLogger('vl_silks.returns')

returns_bp = Blueprint('returns', __name__)


def serialize_return(r):
    """Serialize return dict for JSON output."""
    if not r:
        return None
    r_copy = dict(r)
    for key in ('total_refund_amount', 'original_sale_total'):
        if r_copy.get(key) is not None:
            r_copy[key] = float(r_copy[key])
    for dt_key in ('return_date', 'sale_date', 'created_at'):
        if r_copy.get(dt_key) is not None:
            r_copy[dt_key] = str(r_copy[dt_key])
    if 'items' in r_copy and r_copy['items']:
        r_copy['items'] = [serialize_return_item(it) for it in r_copy['items']]
    return r_copy


def serialize_return_item(item):
    """Serialize return item row for JSON output."""
    if not item:
        return None
    i_copy = dict(item)
    for key in ('unit_price', 'refund_amount', 'effective_unit_price'):
        if i_copy.get(key) is not None:
            i_copy[key] = float(i_copy[key])
    for dt_key in ('created_at',):
        if i_copy.get(dt_key) is not None:
            i_copy[dt_key] = str(i_copy[dt_key])
    return i_copy


# =========================================================================
# WEB ROUTES
# =========================================================================

@returns_bp.route('/returns')
@login_required
def index():
    """
    Returns & Exchanges directory with summary metrics and search/filtering.
    Accessible to both Staff and Admin.
    """
    search = request.args.get('search', '').strip()
    refund_type = request.args.get('refund_type', 'ALL').strip()
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None

    returns_list = return_service.get_all_returns(
        search=search if search else None,
        refund_type=refund_type if refund_type != 'ALL' else None,
        date_from=date_from,
        date_to=date_to
    )

    summary = return_service.get_return_summary_metrics()

    return render_template(
        'returns/index.html',
        returns=returns_list,
        summary=summary,
        current_search=search,
        current_refund_type=refund_type,
        current_date_from=date_from or '',
        current_date_to=date_to or ''
    )


@returns_bp.route('/returns/new', methods=['GET', 'POST'])
@login_required
def new():
    """
    Create a new return or garment exchange.
    Preselects original invoice if `sale_id` query param is supplied.
    """
    if request.method == 'POST':
        action_type = request.form.get('action_type', 'RETURN').upper()
        sale_id = request.form.get('sale_id')
        user_id = session.get('user_id', 1)

        try:
            sale_id_int = int(sale_id)
        except (ValueError, TypeError):
            flash("Invalid or missing original Sale ID.", "danger")
            return redirect(url_for('returns.new'))

        return_date = request.form.get('return_date') or date.today().strftime('%Y-%m-%d')
        return_reason = request.form.get('return_reason', '').strip()

        if action_type == 'RETURN':
            refund_type = request.form.get('refund_type', 'CASH').upper()

            # Parse returned items from dynamic form inputs
            # format: item_qty_{sale_item_id}, item_condition_{sale_item_id}
            items_data = []
            for key, val in request.form.items():
                if key.startswith('item_qty_') and val.strip():
                    try:
                        qty = int(val.strip())
                        if qty > 0:
                            sale_item_id = int(key.replace('item_qty_', ''))
                            condition = request.form.get(f'item_condition_{sale_item_id}', 'RESTOCKABLE')
                            items_data.append({
                                'sale_item_id': sale_item_id,
                                'quantity': qty,
                                'condition_status': condition
                            })
                    except ValueError:
                        continue

            if not items_data:
                flash("Please select at least one item and enter a valid return quantity.", "warning")
                return redirect(url_for('returns.new', sale_id=sale_id_int))

            try:
                res = return_service.create_return(
                    return_data={
                        'sale_id': sale_id_int,
                        'refund_type': refund_type,
                        'return_date': return_date,
                        'return_reason': return_reason
                    },
                    items_data=items_data,
                    user_id=user_id
                )
                flash(f"Return {res['return_reference']} created successfully! Refund: ₹{res['total_refund_amount']} via {res['refund_type']}.", "success")
                return redirect(url_for('returns.view', return_id=res['return_id']))

            except ValidationError as e:
                flash(f"Return Error: {str(e)}", "danger")
                return redirect(url_for('returns.new', sale_id=sale_id_int))
            except Exception as e:
                logger.error(f"Failed to create return: {e}", exc_info=True)
                flash("An unexpected error occurred while processing the return.", "danger")
                return redirect(url_for('returns.new', sale_id=sale_id_int))

        elif action_type == 'EXCHANGE':
            # Exchange workflow: parse old items and replacement items
            old_items_data = []
            for key, val in request.form.items():
                if key.startswith('item_qty_') and val.strip():
                    try:
                        qty = int(val.strip())
                        if qty > 0:
                            sale_item_id = int(key.replace('item_qty_', ''))
                            condition = request.form.get(f'item_condition_{sale_item_id}', 'RESTOCKABLE')
                            old_items_data.append({
                                'sale_item_id': sale_item_id,
                                'quantity': qty,
                                'condition_status': condition
                            })
                    except ValueError:
                        continue

            new_variant_id = request.form.get('exchange_new_variant_id')
            new_quantity = request.form.get('exchange_new_quantity', '1')

            try:
                new_var_id_int = int(new_variant_id)
                new_qty_int = int(new_quantity)
            except (ValueError, TypeError):
                flash("Please select a valid replacement variant and quantity.", "warning")
                return redirect(url_for('returns.new', sale_id=sale_id_int, mode='exchange'))

            new_items_data = [{
                'variant_id': new_var_id_int,
                'quantity': new_qty_int
            }]

            diff_payment_method = request.form.get('diff_payment_method', 'CASH').upper()

            try:
                res = return_service.process_exchange(
                    exchange_data={
                        'sale_id': sale_id_int,
                        'return_date': return_date,
                        'notes': return_reason,
                        'payment_method': diff_payment_method
                    },
                    old_items_data=old_items_data,
                    new_items_data=new_items_data,
                    user_id=user_id
                )
                flash(f"Exchange {res['return_reference']} processed successfully! Price difference: ₹{res['price_difference']}.", "success")
                return redirect(url_for('returns.view', return_id=res['return_id']))

            except ValidationError as e:
                flash(f"Exchange Error: {str(e)}", "danger")
                return redirect(url_for('returns.new', sale_id=sale_id_int, mode='exchange'))
            except Exception as e:
                logger.error(f"Failed to process exchange: {e}", exc_info=True)
                flash("An unexpected error occurred while processing the exchange.", "danger")
                return redirect(url_for('returns.new', sale_id=sale_id_int, mode='exchange'))

    # GET Request: Resolve and load sale details
    mode = request.args.get('mode', 'return')

    # Priority-based resolution for lookup parameters:
    # 1. direct_sale_id if provided (non-empty)
    # 2. selected_sale_id if provided (non-empty)
    # 3. sale_id query parameter(s)
    direct_sale_id = request.args.get('direct_sale_id', '').strip()
    selected_sale_id = request.args.get('selected_sale_id', '').strip()

    if direct_sale_id or selected_sale_id:
        target_raw = direct_sale_id if direct_sale_id else selected_sale_id
        try:
            target_id = int(target_raw)
            # Redirect to clean canonical URL
            if mode and mode != 'return':
                return redirect(url_for('returns.new', sale_id=target_id, mode=mode))
            return redirect(url_for('returns.new', sale_id=target_id))
        except (ValueError, TypeError):
            flash("Invalid Sale ID specified. Please enter a valid numeric ID.", "warning")
            return redirect(url_for('returns.new'))

    # Canonical sale_id resolution (filtering out any blank duplicate values)
    raw_sale_ids = [s.strip() for s in request.args.getlist('sale_id') if s.strip()]
    sale_id_param = raw_sale_ids[-1] if raw_sale_ids else None

    sale = None
    returnable_items = []

    if sale_id_param:
        try:
            sale_id_int = int(sale_id_param)
            sale, returnable_items = return_service.get_sale_returnable_items(sale_id_int)
            if not sale:
                flash(f"Sale #{sale_id_param} was not found.", "warning")
        except (ValueError, TypeError):
            flash("Invalid Sale ID specified. Please enter a valid numeric ID.", "warning")

    # Fetch active sales for dropdown selection if no sale selected
    recent_sales = sale_service.get_all_sales()[:30] if not sale else []
    # Fetch active variants with stock > 0 for exchange picker
    exchange_variants = sale_service.get_active_variants_for_sale()

    return render_template(
        'returns/new.html',
        sale=sale,
        returnable_items=returnable_items,
        recent_sales=recent_sales,
        exchange_variants=exchange_variants,
        mode=mode,
        today=date.today().strftime('%Y-%m-%d')
    )


@returns_bp.route('/returns/<int:return_id>')
@login_required
def view(return_id):
    """
    View complete details of a return/exchange, returned items, condition breakdown,
    and financial/stock audit trail.
    """
    ret = return_service.get_return_by_id(return_id)
    if not ret:
        flash(f"Return record #{return_id} was not found.", "warning")
        return redirect(url_for('returns.index'))

    return render_template('returns/view.html', ret=ret)


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@returns_bp.route('/api/returns', methods=['GET'])
def api_list_returns():
    """
    GET /api/returns
    Retrieve list of customer returns with filtering.
    """
    search = request.args.get('search', '').strip() or None
    refund_type = request.args.get('refund_type', '').strip() or None
    date_from = request.args.get('date_from', '').strip() or None
    date_to = request.args.get('date_to', '').strip() or None

    returns_list = return_service.get_all_returns(
        search=search,
        refund_type=refund_type,
        date_from=date_from,
        date_to=date_to
    )

    return jsonify({
        "status": "success",
        "count": len(returns_list),
        "data": [serialize_return(r) for r in returns_list]
    }), 200


@returns_bp.route('/api/returns/<int:return_id>', methods=['GET'])
def api_get_return(return_id):
    """
    GET /api/returns/:id
    Retrieve detailed return record with items.
    """
    ret = return_service.get_return_by_id(return_id)
    if not ret:
        return jsonify({"status": "error", "message": f"Return #{return_id} not found"}), 404

    return jsonify({
        "status": "success",
        "data": serialize_return(ret)
    }), 200


@returns_bp.route('/api/returns/sale/<int:sale_id>/returnable-items', methods=['GET'])
def api_get_sale_returnable_items(sale_id):
    """
    GET /api/returns/sale/:sale_id/returnable-items
    Calculate returnable quantity breakdown for a sale.
    """
    sale, returnable_items = return_service.get_sale_returnable_items(sale_id)
    if not sale:
        return jsonify({"status": "error", "message": f"Sale #{sale_id} not found"}), 404

    return jsonify({
        "status": "success",
        "sale": {
            "sale_id": sale['sale_id'],
            "invoice_number": sale['invoice_number'],
            "sale_date": str(sale['sale_date']),
            "total_amount": float(sale['total_amount']),
            "customer_id": sale['customer_id'],
            "customer_name": sale['customer_name']
        },
        "count": len(returnable_items),
        "items": [serialize_return_item(it) for it in returnable_items]
    }), 200


@returns_bp.route('/api/returns/sales/search', methods=['GET'])
@login_required
def api_search_sales_for_returns():
    """
    GET /api/returns/sales/search?q=<term>&limit=<n>
    Search sales eligible for return processing by:
    - Invoice number (partial)
    - Sale ID (exact numeric)
    - Customer name (partial)
    - Customer phone (partial)
    - Product SKU in the sale (partial)
    Returns summary rows with returnable_items_count so the UI can
    clearly mark fully-returned sales.
    Requires login.
    """
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({
            "status": "error",
            "message": "Search query is required. Provide ?q=<invoice/customer/phone/SKU>"
        }), 400

    try:
        limit = min(int(request.args.get('limit', 20)), 50)
    except (ValueError, TypeError):
        limit = 20

    results = return_service.search_sales_for_returns(q, limit=limit)
    return jsonify({
        "status": "success",
        "query": q,
        "count": len(results),
        "data": results
    }), 200


@returns_bp.route('/api/returns', methods=['POST'])
def api_create_return():
    """
    POST /api/returns
    Process an atomic customer garment return.
    """
    if 'user_id' not in session and not request.is_json:
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    data = request.get_json() or {}
    user_id = session.get('user_id') or data.get('user_id', 1)

    return_data = {
        'sale_id': data.get('sale_id'),
        'refund_type': data.get('refund_type', 'CASH'),
        'return_date': data.get('return_date'),
        'return_reason': data.get('return_reason'),
        'customer_id': data.get('customer_id')
    }
    items_data = data.get('items') or []

    try:
        res = return_service.create_return(return_data, items_data, user_id)
        return jsonify({
            "status": "success",
            "message": f"Return {res['return_reference']} created successfully",
            "data": {
                "return_id": res['return_id'],
                "return_reference": res['return_reference'],
                "sale_id": res['sale_id'],
                "invoice_number": res['invoice_number'],
                "total_refund_amount": float(res['total_refund_amount']),
                "refund_type": res['refund_type'],
                "item_count": res['item_count'],
                "items": res['items']
            }
        }), 201

    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"API return creation error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@returns_bp.route('/api/returns/exchange', methods=['POST'])
def api_process_exchange():
    """
    POST /api/returns/exchange
    Process an atomic garment exchange.
    """
    if 'user_id' not in session and not request.is_json:
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    data = request.get_json() or {}
    user_id = session.get('user_id') or data.get('user_id', 1)

    exchange_data = {
        'sale_id': data.get('sale_id'),
        'return_date': data.get('return_date'),
        'notes': data.get('notes') or data.get('return_reason'),
        'payment_method': data.get('payment_method', 'CASH'),
        'customer_id': data.get('customer_id')
    }
    old_items_data = data.get('old_items') or data.get('return_items') or []
    new_items_data = data.get('new_items') or data.get('exchange_items') or []

    try:
        res = return_service.process_exchange(exchange_data, old_items_data, new_items_data, user_id)
        return jsonify({
            "status": "success",
            "message": f"Exchange {res['return_reference']} processed successfully",
            "data": {
                "return_id": res['return_id'],
                "return_reference": res['return_reference'],
                "sale_id": res['sale_id'],
                "invoice_number": res['invoice_number'],
                "old_total_value": float(res['old_total_value']),
                "new_total_value": float(res['new_total_value']),
                "price_difference": float(res['price_difference']),
                "payment_status": res['payment_status']
            }
        }), 201

    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logger.error(f"API exchange error: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
