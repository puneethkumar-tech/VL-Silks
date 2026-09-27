import re
import logging
from werkzeug.security import generate_password_hash
from backend.utils.database import get_db_cursor, query_db

logger = logging.getLogger('vl_silks.user_service')


class ValidationError(Exception):
    """Custom exception for user business validation errors."""
    pass


def get_all_users(search=None, role=None, status=None):
    """
    Fetch all users with optional search, role, and status filters.
    """
    sql = """
        SELECT
            user_id,
            name,
            email,
            role,
            status,
            created_at,
            updated_at
        FROM users
        WHERE 1=1
    """
    params = []

    if role and role.upper() != 'ALL':
        sql += " AND role = %s"
        params.append(role.upper())

    if status and status.upper() != 'ALL':
        sql += " AND status = %s"
        params.append(status.upper())

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (name LIKE %s OR email LIKE %s)"
        params.extend([search_term, search_term])

    sql += " ORDER BY user_id ASC"
    return query_db(sql, tuple(params) if params else None)


def get_user_by_id(user_id):
    """Fetch a single user by ID."""
    sql = """
        SELECT
            user_id,
            name,
            email,
            role,
            status,
            created_at,
            updated_at
        FROM users
        WHERE user_id = %s
    """
    return query_db(sql, (user_id,), one=True)


def get_user_by_email(email):
    """Fetch a single user by email."""
    sql = """
        SELECT
            user_id,
            name,
            email,
            role,
            status,
            created_at,
            updated_at
        FROM users
        WHERE email = %s
    """
    return query_db(sql, (email.strip().lower(),), one=True)


def create_user(user_data):
    """
    Create a new user with validation.
    user_data must contain:
      - name: non-empty string
      - email: valid email string
      - password: at least 6 characters
      - role: 'ADMIN' or 'STAFF' (default 'STAFF')
      - status: 'ACTIVE' or 'INACTIVE' (default 'ACTIVE')
    """
    name = user_data.get('name', '').strip()
    email = user_data.get('email', '').strip().lower()
    password = user_data.get('password', '')
    role = user_data.get('role', 'STAFF').strip().upper()
    status = user_data.get('status', 'ACTIVE').strip().upper()

    if not name:
        raise ValidationError("Full name is required.")
    if len(name) > 100:
        raise ValidationError("Full name cannot exceed 100 characters.")

    if not email:
        raise ValidationError("Email address is required.")
    if len(email) > 100:
        raise ValidationError("Email address cannot exceed 100 characters.")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise ValidationError("Invalid email address format.")

    if not password:
        raise ValidationError("Password is required.")
    if len(password) < 6:
        raise ValidationError("Password must be at least 6 characters long.")

    if role not in ['ADMIN', 'STAFF']:
        raise ValidationError("Role must be either 'ADMIN' or 'STAFF'.")

    if status not in ['ACTIVE', 'INACTIVE']:
        raise ValidationError("Status must be either 'ACTIVE' or 'INACTIVE'.")

    # Check for duplicate email
    existing = get_user_by_email(email)
    if existing:
        raise ValidationError(f"A user with email '{email}' already exists.")

    password_hash = generate_password_hash(password)

    sql = """
        INSERT INTO users (name, email, password_hash, role, status)
        VALUES (%s, %s, %s, %s, %s)
    """
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(sql, (name, email, password_hash, role, status))
        user_id = cursor.lastrowid

    logger.info(f"User created: {user_id} ({name}, {role})")
    return user_id


def update_user(user_id, user_data):
    """
    Update an existing user's details.
    user_data may contain:
      - name: non-empty string
      - email: valid email string
      - password: optional string (if provided and non-empty, updates password)
      - role: 'ADMIN' or 'STAFF'
      - status: 'ACTIVE' or 'INACTIVE'
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValidationError(f"User ID {user_id} not found.")

    name = user_data.get('name', user['name']).strip()
    email = user_data.get('email', user['email']).strip().lower()
    password = user_data.get('password', '')
    role = user_data.get('role', user['role']).strip().upper()
    status = user_data.get('status', user['status']).strip().upper()

    if not name:
        raise ValidationError("Full name is required.")
    if len(name) > 100:
        raise ValidationError("Full name cannot exceed 100 characters.")

    if not email:
        raise ValidationError("Email address is required.")
    if len(email) > 100:
        raise ValidationError("Email address cannot exceed 100 characters.")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        raise ValidationError("Invalid email address format.")

    if role not in ['ADMIN', 'STAFF']:
        raise ValidationError("Role must be either 'ADMIN' or 'STAFF'.")

    if status not in ['ACTIVE', 'INACTIVE']:
        raise ValidationError("Status must be either 'ACTIVE' or 'INACTIVE'.")

    # Check email uniqueness against other users
    existing = get_user_by_email(email)
    if existing and existing['user_id'] != user_id:
        raise ValidationError(f"Email '{email}' is already in use by another user.")

    # Safety check: Cannot demote or deactivate the last active Admin
    if user['role'] == 'ADMIN' and user['status'] == 'ACTIVE':
        if role != 'ADMIN' or status != 'ACTIVE':
            active_admins = query_db(
                "SELECT COUNT(*) AS count FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE' AND user_id != %s",
                (user_id,),
                one=True
            )
            if active_admins['count'] == 0:
                raise ValidationError("Cannot demote or deactivate the only active Administrator in the system.")

    update_fields = ["name = %s", "email = %s", "role = %s", "status = %s"]
    params = [name, email, role, status]

    if password and password.strip():
        if len(password.strip()) < 6:
            raise ValidationError("New password must be at least 6 characters long.")
        password_hash = generate_password_hash(password.strip())
        update_fields.append("password_hash = %s")
        params.append(password_hash)

    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"

    with get_db_cursor(commit=True) as cursor:
        cursor.execute(sql, tuple(params))

    logger.info(f"User updated: {user_id}")
    return True


def toggle_user_status(user_id):
    """
    Toggle a user's status between 'ACTIVE' and 'INACTIVE'.
    Enforces that the last active Admin cannot be deactivated.
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValidationError(f"User ID {user_id} not found.")

    new_status = 'INACTIVE' if user['status'] == 'ACTIVE' else 'ACTIVE'

    # Safety check: Cannot deactivate the last active Admin
    if user['role'] == 'ADMIN' and user['status'] == 'ACTIVE' and new_status == 'INACTIVE':
        active_admins = query_db(
            "SELECT COUNT(*) AS count FROM users WHERE role = 'ADMIN' AND status = 'ACTIVE' AND user_id != %s",
            (user_id,),
            one=True
        )
        if active_admins['count'] == 0:
            raise ValidationError("Cannot deactivate the only active Administrator in the system.")

    sql = "UPDATE users SET status = %s WHERE user_id = %s"
    with get_db_cursor(commit=True) as cursor:
        cursor.execute(sql, (new_status, user_id))

    logger.info(f"User {user_id} status toggled to {new_status}")
    return new_status
