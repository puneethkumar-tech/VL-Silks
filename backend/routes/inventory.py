import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import inventory_service, product_service
from backend.services.inventory_service import ValidationError

logger = logging.getLogger('vl_silks.inventory')

inventory_bp = Blueprint('inventory', __name__)


# =========================================================================
# WEB ROUTES
# =========================================================================

@inventory_bp.route('/inventory')
@login_required
def index():
    """
    Main inventory dashboard & current stock directory.
    Supports search across product name, brand, SKU, color, barcode, and filters by category and stock status.
    """
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', '').strip()
    stock_status = request.args.get('stock_status', 'ALL').strip()
    status = request.args.get('status', 'ACTIVE').strip()

    try:
        category_id_int = int(category_id) if category_id else None
    except ValueError:
        category_id_int = None

    items = inventory_service.get_inventory(
        search=search if search else None,
        category_id=category_id_int,
        status=status if status != 'ALL' else None,
        stock_status=stock_status if stock_status != 'ALL' else None
    )

    metrics = inventory_service.get_inventory_summary_metrics()
    categories = product_service.get_all_categories(status='ACTIVE')

    return render_template(
        'inventory/index.html',
        items=items,
        metrics=metrics,
        categories=categories,
        current_search=search,
        current_category_id=category_id,
        current_stock_status=stock_status,
        current_status=status
    )


@inventory_bp.route('/inventory/low-stock')
@login_required
def low_stock():
    """
    Low Stock alerts page showing items at or below minimum stock threshold.
    """
    low_stock_items = inventory_service.get_low_stock_items()
    metrics = inventory_service.get_inventory_summary_metrics()

    return render_template(
        'inventory/low_stock.html',
        items=low_stock_items,
        metrics=metrics
    )


@inventory_bp.route('/inventory/out-of-stock')
@login_required
def out_of_stock():
    """
    Out of Stock alerts page showing items with zero stock.
    """
    out_of_stock_items = inventory_service.get_out_of_stock_items()
    metrics = inventory_service.get_inventory_summary_metrics()

    return render_template(
        'inventory/out_of_stock.html',
        items=out_of_stock_items,
        metrics=metrics
    )


@inventory_bp.route('/inventory/movements')
@login_required
def movements():
    """
    Stock Movement Audit Log displaying full chronological inventory transaction history.
    """
    movement_type = request.args.get('movement_type', 'ALL').strip()
    reference_type = request.args.get('reference_type', 'ALL').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    search = request.args.get('search', '').strip()

    movements_list = inventory_service.get_stock_movements(
        movement_type=movement_type if movement_type != 'ALL' else None,
        reference_type=reference_type if reference_type != 'ALL' else None,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        search=search if search else None,
        limit=200
    )

    return render_template(
        'inventory/movements.html',
        movements=movements_list,
        current_movement_type=movement_type,
        current_reference_type=reference_type,
        current_date_from=date_from,
        current_date_to=date_to,
        current_search=search
    )


@inventory_bp.route('/inventory/adjustment', methods=['GET', 'POST'])
@admin_required
def adjustment():
    """
    Manual Stock Adjustment and Damaged Stock Recording (Admin Only).
    """
    if request.method == 'POST':
        action_type = request.form.get('action_type', 'ADJUSTMENT').strip().upper()
        variant_id = request.form.get('variant_id')
        quantity = request.form.get('quantity')
        reason = request.form.get('reason', '').strip()
        adjustment_type = request.form.get('adjustment_type', 'INCREASE').strip().upper()
        user_id = session.get('user_id')

        try:
            if action_type == 'DAMAGE':
                result = inventory_service.record_damaged_stock(
                    variant_id=variant_id,
                    quantity=quantity,
                    reason=reason,
                    user_id=user_id
                )
                flash(f"Damaged stock recorded for '{result['sku']}' ({result['product_name']}). Wrote off {result['damaged_quantity']} units. New stock: {result['new_stock']}.", "warning")
            else:
                result = inventory_service.adjust_stock(
                    variant_id=variant_id,
                    adjustment_type=adjustment_type,
                    quantity=quantity,
                    reason=reason,
                    user_id=user_id
                )
                flash(f"Stock adjusted for '{result['sku']}' ({result['product_name']}). Delta: {result['delta']:+d}. New stock: {result['new_stock']}.", "success")

            return redirect(url_for('inventory.index'))

        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
        except Exception as e:
            logger.error(f"Stock adjustment error: {e}")
            flash(f"System Error: Unable to adjust stock. {str(e)}", "danger")

    # GET or validation error
    prefill_variant_id = request.args.get('variant_id')
    variants = inventory_service.get_inventory(status='ACTIVE')
    return render_template(
        'inventory/adjustment.html',
        variants=variants,
        prefill_variant_id=prefill_variant_id
    )


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@inventory_bp.route('/api/inventory', methods=['GET'])
def api_get_inventory():
    """
    GET /api/inventory
    Retrieve all inventory items with computed stock status and query filtering.
    """
    search = request.args.get('search')
    category_id = request.args.get('category_id')
    status = request.args.get('status')
    stock_status = request.args.get('stock_status')

    try:
        category_id_int = int(category_id) if category_id else None
    except ValueError:
        category_id_int = None

    items = inventory_service.get_inventory(
        search=search,
        category_id=category_id_int,
        status=status if status and status.upper() != 'ALL' else None,
        stock_status=stock_status if stock_status and stock_status.upper() != 'ALL' else None
    )

    serialized = []
    for item in items:
        it = dict(item)
        for key in ('purchase_price', 'selling_price'):
            if it.get(key) is not None:
                it[key] = float(it[key])
        if it.get('updated_at'):
            it['updated_at'] = str(it['updated_at'])
        serialized.append(it)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'inventory': serialized
    }), 200


@inventory_bp.route('/api/inventory/low-stock', methods=['GET'])
def api_get_low_stock():
    """
    GET /api/inventory/low-stock
    Retrieve list of active variants where stock is low (0 < stock <= min_stock).
    """
    items = inventory_service.get_low_stock_items()
    serialized = []
    for item in items:
        it = dict(item)
        for key in ('purchase_price', 'selling_price'):
            if it.get(key) is not None:
                it[key] = float(it[key])
        serialized.append(it)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'low_stock_items': serialized
    }), 200


@inventory_bp.route('/api/inventory/movements', methods=['GET'])
def api_get_movements():
    """
    GET /api/inventory/movements
    Retrieve chronological audit trail of stock movements.
    """
    variant_id = request.args.get('variant_id')
    movement_type = request.args.get('movement_type')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    search = request.args.get('search')

    try:
        variant_id_int = int(variant_id) if variant_id else None
    except ValueError:
        variant_id_int = None

    movements = inventory_service.get_stock_movements(
        variant_id=variant_id_int,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=200
    )

    serialized = []
    for m in movements:
        md = dict(m)
        if md.get('movement_date'):
            md['movement_date'] = str(md['movement_date'])
        serialized.append(md)

    return jsonify({
        'status': 'success',
        'count': len(serialized),
        'movements': serialized
    }), 200


@inventory_bp.route('/api/inventory/adjustment', methods=['POST'])
def api_stock_adjustment():
    """
    POST /api/inventory/adjustment
    Atomically adjust variant stock or record damaged stock write-off (Admin Only).
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({'status': 'error', 'message': 'Admin authorization required'}), 403

    data = request.get_json() or {}
    variant_id = data.get('variant_id')
    adjustment_type = (data.get('adjustment_type') or 'INCREASE').strip().upper()
    quantity = data.get('quantity')
    reason = data.get('reason')
    user_id = session.get('user_id') or data.get('user_id')

    if not user_id:
        return jsonify({'status': 'error', 'message': 'Authenticated user ID is required'}), 401

    try:
        if adjustment_type == 'DAMAGE':
            result = inventory_service.record_damaged_stock(
                variant_id=variant_id,
                quantity=quantity,
                reason=reason,
                user_id=user_id
            )
        else:
            result = inventory_service.adjust_stock(
                variant_id=variant_id,
                adjustment_type=adjustment_type,
                quantity=quantity,
                reason=reason,
                user_id=user_id
            )

        return jsonify({
            'status': 'success',
            'message': 'Stock adjusted successfully and audit record created',
            'data': result
        }), 200

    except ValidationError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"API adjustment failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
