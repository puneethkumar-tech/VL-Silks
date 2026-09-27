from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash
from backend.utils.database import query_db

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    """Decorator to require login for web routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role for web routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') != 'ADMIN':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Forbidden', 'message': 'Administrator access required'}), 403
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Web login route."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        user = query_db(
            "SELECT user_id, name, email, password_hash, role, status FROM users WHERE email = %s",
            (email,),
            one=True
        )

        if user and user['status'] == 'ACTIVE' and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            flash(f"Welcome back, {user['name']}!", 'success')
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Web logout route."""
    session.clear()
    flash('You have been safely logged out.', 'info')
    return redirect(url_for('auth.login'))

# API Authentication Endpoints
@auth_bp.route('/api/auth/login', methods=['POST'])
def api_login():
    """API Login endpoint."""
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = query_db(
        "SELECT user_id, name, email, password_hash, role, status FROM users WHERE email = %s",
        (email,),
        one=True
    )

    if user and user['status'] == 'ACTIVE' and check_password_hash(user['password_hash'], password):
        session['user_id'] = user['user_id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        return jsonify({
            "message": "Login successful",
            "user": {
                "id": user['user_id'],
                "name": user['name'],
                "email": user['email'],
                "role": user['role']
            }
        }), 200

    return jsonify({"error": "Invalid email or password"}), 401

@auth_bp.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API Logout endpoint."""
    session.clear()
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/api/auth/me', methods=['GET'])
def api_me():
    """API current user endpoint."""
    if 'user_id' not in session:
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "user": {
            "id": session['user_id'],
            "name": session['user_name'],
            "email": session['user_email'],
            "role": session['user_role']
        }
    }), 200
