from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import category_service
from backend.services.category_service import ValidationError

categories_bp = Blueprint('categories', __name__)

# =========================================================================
# WEB ROUTES
# =========================================================================

@categories_bp.route('/categories')
@login_required
def index():
    """List all categories with product counts, search, and status filters."""
    search = request.args.get('search', '').strip()
    status = request.args.get('status', 'ALL').strip()

    categories_list = category_service.get_all_categories(
        search=search if search else None,
        status=status if status != 'ALL' else None,
        include_counts=True
    )

    total_categories_count = len(categories_list)
    total_products_sum = sum(c.get('product_count', 0) for c in categories_list)
    active_categories_count = sum(1 for c in categories_list if c.get('status') == 'ACTIVE')

    return render_template(
        'categories/index.html',
        categories=categories_list,
        current_search=search,
        current_status=status,
        total_categories_count=total_categories_count,
        total_products_sum=total_products_sum,
        active_categories_count=active_categories_count
    )

@categories_bp.route('/categories/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Add a new garment category (Admin Only)."""
    if request.method == 'POST':
        category_data = {
            'category_name': request.form.get('category_name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'status': request.form.get('status', 'ACTIVE')
        }

        try:
            category_id = category_service.create_category(category_data)
            flash(f"Category '{category_data['category_name']}' created successfully!", "success")
            return redirect(url_for('categories.index'))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('categories/new.html', form_data=category_data)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template('categories/new.html', form_data=category_data)

    return render_template('categories/new.html', form_data={})

@categories_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(category_id):
    """Edit an existing category's name and description (Admin Only)."""
    category = category_service.get_category_by_id(category_id, include_counts=True)
    if not category:
        flash("Category not found.", "danger")
        return redirect(url_for('categories.index'))

    if request.method == 'POST':
        category_data = {
            'category_name': request.form.get('category_name', '').strip(),
            'description': request.form.get('description', '').strip(),
            'status': request.form.get('status', category['status'])
        }

        try:
            category_service.update_category(category_id, category_data)
            flash(f"Category '{category_data['category_name']}' updated successfully!", "success")
            return redirect(url_for('categories.index'))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('categories/edit.html', category=category, form_data=category_data)
        except Exception as e:
            flash(f"Error updating category: {str(e)}", "danger")
            return render_template('categories/edit.html', category=category, form_data=category_data)

    return render_template('categories/edit.html', category=category, form_data=category)

@categories_bp.route('/categories/<int:category_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(category_id):
    """Safely toggle active/inactive status of a category (Admin Only)."""
    try:
        new_status = category_service.toggle_category_status(category_id)
        flash(f"Category status updated to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update category status: {str(e)}", "danger")
    return redirect(request.referrer or url_for('categories.index'))


# =========================================================================
# REST API ENDPOINTS (API_SPEC.md)
# =========================================================================

@categories_bp.route('/api/categories', methods=['GET'])
def api_get_categories():
    """GET /api/categories - List categories with optional search and status filter."""
    search = request.args.get('search')
    status = request.args.get('status')

    categories_list = category_service.get_all_categories(
        search=search,
        status=status,
        include_counts=True
    )
    return jsonify({
        "status": "success",
        "count": len(categories_list),
        "data": categories_list
    }), 200

@categories_bp.route('/api/categories/<int:category_id>', methods=['GET'])
def api_get_category(category_id):
    """GET /api/categories/:id - Single category with product count."""
    category = category_service.get_category_by_id(category_id, include_counts=True)
    if not category:
        return jsonify({"status": "error", "message": "Category not found"}), 404

    return jsonify({"status": "success", "data": category}), 200

@categories_bp.route('/api/categories', methods=['POST'])
def api_create_category():
    """POST /api/categories - Create a new category (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    try:
        category_id = category_service.create_category(data)
        return jsonify({
            "status": "success",
            "message": "Category created successfully",
            "category_id": category_id
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@categories_bp.route('/api/categories/<int:category_id>', methods=['PUT'])
def api_update_category(category_id):
    """PUT /api/categories/:id - Update an existing category (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    category = category_service.get_category_by_id(category_id, include_counts=False)
    if not category:
        return jsonify({"status": "error", "message": "Category not found"}), 404

    data = request.get_json() or {}
    try:
        category_service.update_category(category_id, data)
        return jsonify({"status": "success", "message": "Category updated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@categories_bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
def api_delete_category(category_id):
    """
    DELETE /api/categories/:id - Safe deactivation of category (Admin Only).
    Does NOT physically delete the category or its referencing products.
    """
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        category_service.delete_category(category_id)
        return jsonify({
            "status": "success",
            "message": "Category safely deactivated. Existing product relationships are preserved."
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
