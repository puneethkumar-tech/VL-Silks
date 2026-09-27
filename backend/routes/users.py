from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import admin_required
from backend.services import user_service
from backend.services.user_service import ValidationError

users_bp = Blueprint('users', __name__)


# =========================================================================
# WEB ROUTES (Admin Only)
# =========================================================================

@users_bp.route('/users')
@admin_required
def index():
    """List all system users with search, role, and status filters."""
    search = request.args.get('search', '').strip()
    role = request.args.get('role', 'ALL').strip()
    status = request.args.get('status', 'ALL').strip()

    users_list = user_service.get_all_users(
        search=search if search else None,
        role=role if role != 'ALL' else None,
        status=status if status != 'ALL' else None
    )

    all_users = user_service.get_all_users()
    total_users_count = len(all_users)
    active_users_count = sum(1 for u in all_users if u.get('status') == 'ACTIVE')
    staff_count = sum(1 for u in all_users if u.get('role') == 'STAFF')
    admin_count = sum(1 for u in all_users if u.get('role') == 'ADMIN')

    return render_template(
        'users/index.html',
        users=users_list,
        current_search=search,
        current_role=role,
        current_status=status,
        total_users_count=total_users_count,
        active_users_count=active_users_count,
        staff_count=staff_count,
        admin_count=admin_count
    )


@users_bp.route('/users/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Create a new user account (Admin Only)."""
    if request.method == 'POST':
        user_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'password': request.form.get('password', ''),
            'role': request.form.get('role', 'STAFF').strip().upper(),
            'status': request.form.get('status', 'ACTIVE').strip().upper()
        }

        try:
            user_id = user_service.create_user(user_data)
            flash(f"User '{user_data['name']}' created successfully!", "success")
            return redirect(url_for('users.index'))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('users/new.html', form_data=user_data)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template('users/new.html', form_data=user_data)

    return render_template('users/new.html', form_data={'role': 'STAFF', 'status': 'ACTIVE'})


@users_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(user_id):
    """Edit user details, role, and status (Admin Only)."""
    user = user_service.get_user_by_id(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('users.index'))

    if request.method == 'POST':
        user_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'password': request.form.get('password', ''),
            'role': request.form.get('role', user['role']).strip().upper(),
            'status': request.form.get('status', user['status']).strip().upper()
        }

        try:
            user_service.update_user(user_id, user_data)
            flash(f"User '{user_data['name']}' updated successfully!", "success")
            return redirect(url_for('users.index'))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template('users/edit.html', user=user, form_data=user_data)
        except Exception as e:
            flash(f"Error updating user: {str(e)}", "danger")
            return render_template('users/edit.html', user=user, form_data=user_data)

    return render_template('users/edit.html', user=user, form_data=user)


@users_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(user_id):
    """Safely toggle active/inactive status of a user (Admin Only)."""
    try:
        new_status = user_service.toggle_user_status(user_id)
        flash(f"User status updated to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update user status: {str(e)}", "danger")
    return redirect(request.referrer or url_for('users.index'))


# =========================================================================
# REST API ENDPOINTS (Admin Only)
# =========================================================================

@users_bp.route('/api/users', methods=['GET'])
def api_get_users():
    """GET /api/users — List all users (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    search = request.args.get('search')
    role = request.args.get('role')
    status = request.args.get('status')
    users_list = user_service.get_all_users(search=search, role=role, status=status)
    return jsonify({
        "status": "success",
        "count": len(users_list),
        "data": users_list
    }), 200


@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
def api_get_user(user_id):
    """GET /api/users/:id — Get user by ID (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    user = user_service.get_user_by_id(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    return jsonify({"status": "success", "data": user}), 200


@users_bp.route('/api/users', methods=['POST'])
def api_create_user():
    """POST /api/users — Create a new user (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    try:
        user_id = user_service.create_user(data)
        new_user = user_service.get_user_by_id(user_id)
        return jsonify({
            "status": "success",
            "message": "User created successfully",
            "data": new_user
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    """PUT /api/users/:id — Update a user (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    try:
        user_service.update_user(user_id, data)
        updated_user = user_service.get_user_by_id(user_id)
        return jsonify({
            "status": "success",
            "message": "User updated successfully",
            "data": updated_user
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500


@users_bp.route('/api/users/<int:user_id>/toggle-status', methods=['POST'])
def api_toggle_user_status(user_id):
    """POST /api/users/:id/toggle-status — Toggle user active/inactive status (Admin Only)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        new_status = user_service.toggle_user_status(user_id)
        return jsonify({
            "status": "success",
            "message": f"User status updated to {new_status}",
            "new_status": new_status
        }), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500
