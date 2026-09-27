from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import supplier_service
from backend.services.supplier_service import ValidationError

suppliers_bp = Blueprint('suppliers', __name__)


# =========================================================================
# WEB ROUTES
# =========================================================================

@suppliers_bp.route('/suppliers')
@login_required
def index():
    """List all suppliers with purchase counts, search, and status filters."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'ALL').strip()

    suppliers_list = supplier_service.get_all_suppliers(
        search=search if search else None,
        status=status if status != 'ALL' else None
    )

    total_suppliers_count = len(suppliers_list)
    active_suppliers_count = sum(1 for s in suppliers_list if s.get('status') == 'ACTIVE')
    total_purchase_value = sum(s.get('total_purchase_value', 0) or 0 for s in suppliers_list)

    return render_template(
        'suppliers/index.html',
        suppliers=suppliers_list,
        current_search=search,
        current_status=status,
        total_suppliers_count=total_suppliers_count,
        active_suppliers_count=active_suppliers_count,
        total_purchase_value=total_purchase_value
    )


@suppliers_bp.route('/suppliers/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Add a new supplier (Admin Only)."""
    if request.method == 'POST':
        supplier_data = {
            'supplier_name': request.form.get('supplier_name', '').strip(),
            'contact_person': request.form.get('contact_person', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip(),
            'address': request.form.get('address', '').strip(),
            'gst_number': request.form.get('gst_number', '').strip(),
            'status': request.form.get('status', 'ACTIVE')
        }

        try:
            supplier_id = supplier_service.create_supplier(supplier_data)
            flash(f"Supplier '{supplier_data['supplier_name']}' added successfully!", "success")
            return redirect(url_for('suppliers.view', supplier_id=supplier_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('suppliers/new.html', form_data=supplier_data)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template('suppliers/new.html', form_data=supplier_data)

    return render_template('suppliers/new.html', form_data={})


@suppliers_bp.route('/suppliers/<int:supplier_id>')
@login_required
def view(supplier_id):
    """View supplier profile with purchase history."""
    supplier = supplier_service.get_supplier_by_id(supplier_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.index'))

    purchases = supplier_service.get_supplier_purchase_history(supplier_id)

    return render_template(
        'suppliers/view.html',
        supplier=supplier,
        purchases=purchases
    )


@suppliers_bp.route('/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(supplier_id):
    """Edit an existing supplier's details (Admin Only)."""
    supplier = supplier_service.get_supplier_by_id(supplier_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.index'))

    if request.method == 'POST':
        supplier_data = {
            'supplier_name': request.form.get('supplier_name', '').strip(),
            'contact_person': request.form.get('contact_person', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip(),
            'address': request.form.get('address', '').strip(),
            'gst_number': request.form.get('gst_number', '').strip(),
            'status': request.form.get('status', supplier['status'])
        }

        try:
            supplier_service.update_supplier(supplier_id, supplier_data)
            flash(f"Supplier '{supplier_data['supplier_name']}' updated successfully!", "success")
            return redirect(url_for('suppliers.view', supplier_id=supplier_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('suppliers/edit.html', supplier=supplier, form_data=supplier_data)
        except Exception as e:
            flash(f"Error updating supplier: {str(e)}", "danger")
            return render_template('suppliers/edit.html', supplier=supplier, form_data=supplier_data)

    return render_template('suppliers/edit.html', supplier=supplier, form_data=supplier)


@suppliers_bp.route('/suppliers/<int:supplier_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(supplier_id):
    """Safely toggle active/inactive status of a supplier (Admin Only)."""
    try:
        new_status = supplier_service.toggle_supplier_status(supplier_id)
        flash(f"Supplier status updated to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update supplier status: {str(e)}", "danger")
    return redirect(request.referrer or url_for('suppliers.index'))


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@suppliers_bp.route('/api/suppliers', methods=['GET'])
def api_get_suppliers():
    """GET /api/suppliers — List suppliers with optional search and status filter."""
    search = request.args.get('search')
    status = request.args.get('status')
    suppliers_list = supplier_service.get_all_suppliers(search=search, status=status)
    return jsonify({
        "status": "success",
        "count": len(suppliers_list),
        "data": suppliers_list
    }), 200


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['GET'])
def api_get_supplier(supplier_id):
    """GET /api/suppliers/:id — Single supplier with purchase summary."""
    supplier = supplier_service.get_supplier_by_id(supplier_id)
    if not supplier:
        return jsonify({"status": "error", "message": "Supplier not found"}), 404
    return jsonify({"status": "success", "data": supplier}), 200


@suppliers_bp.route('/api/suppliers/<int:supplier_id>/purchases', methods=['GET'])
def api_get_supplier_purchases(supplier_id):
    """GET /api/suppliers/:id/purchases — Purchase history for supplier."""
    supplier = supplier_service.get_supplier_by_id(supplier_id)
    if not supplier:
        return jsonify({"status": "error", "message": "Supplier not found"}), 404

    purchases = supplier_service.get_supplier_purchase_history(supplier_id)
    return jsonify({
        "status": "success",
        "supplier_id": supplier_id,
        "count": len(purchases),
        "data": purchases
    }), 200


@suppliers_bp.route('/api/suppliers', methods=['POST'])
def api_create_supplier():
    """POST /api/suppliers — Create a new supplier (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    try:
        supplier_id = supplier_service.create_supplier(data)
        return jsonify({
            "status": "success",
            "message": "Supplier created successfully",
            "supplier_id": supplier_id
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['PUT'])
def api_update_supplier(supplier_id):
    """PUT /api/suppliers/:id — Update an existing supplier (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    supplier = supplier_service.get_supplier_by_id(supplier_id)
    if not supplier:
        return jsonify({"status": "error", "message": "Supplier not found"}), 404

    data = request.get_json() or {}
    try:
        supplier_service.update_supplier(supplier_id, data)
        return jsonify({"status": "success", "message": "Supplier updated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@suppliers_bp.route('/api/suppliers/<int:supplier_id>', methods=['DELETE'])
def api_delete_supplier(supplier_id):
    """
    DELETE /api/suppliers/:id — Safe deactivation of supplier (Admin Only).
    Preserves all historical purchase records.
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        supplier_service.delete_supplier(supplier_id)
        return jsonify({
            "status": "success",
            "message": "Supplier safely deactivated. Purchase history preserved."
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
