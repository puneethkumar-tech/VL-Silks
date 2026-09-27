import logging
from backend.utils.database import get_db_cursor, query_db

logger = logging.getLogger('vl_silks.category_service')

class ValidationError(Exception):
    """Custom exception for category business validation errors."""
    pass

def get_all_categories(search=None, status=None, include_counts=True):
    """
    Fetch all garment categories with product count.
    Supports search across category_name and description.
    """
    if include_counts:
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                c.description,
                c.status,
                c.created_at,
                c.updated_at,
                COUNT(p.product_id) AS product_count,
                COALESCE(SUM(pv.stock_quantity), 0) AS total_stock
            FROM categories c
            LEFT JOIN products p ON c.category_id = p.category_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id
            WHERE 1=1
        """
    else:
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                c.description,
                c.status,
                c.created_at,
                c.updated_at
            FROM categories c
            WHERE 1=1
        """
    params = []

    if status and status.upper() != 'ALL':
        sql += " AND c.status = %s"
        params.append(status.upper())

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (c.category_name LIKE %s OR c.description LIKE %s)"
        params.extend([search_term, search_term])

    if include_counts:
        sql += " GROUP BY c.category_id ORDER BY c.category_name ASC"
    else:
        sql += " ORDER BY c.category_name ASC"

    return query_db(sql, tuple(params))

def get_category_by_id(category_id, include_counts=True):
    """Fetch single category by ID with associated product count."""
    if include_counts:
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                c.description,
                c.status,
                c.created_at,
                c.updated_at,
                COUNT(p.product_id) AS product_count,
                COALESCE(SUM(pv.stock_quantity), 0) AS total_stock
            FROM categories c
            LEFT JOIN products p ON c.category_id = p.category_id
            LEFT JOIN product_variants pv ON p.product_id = pv.product_id
            WHERE c.category_id = %s
            GROUP BY c.category_id
        """
    else:
        sql = """
            SELECT 
                category_id,
                category_name,
                description,
                status,
                created_at,
                updated_at
            FROM categories
            WHERE category_id = %s
        """
    return query_db(sql, (category_id,), one=True)

def validate_category_data(data, existing_category_id=None):
    """
    Validate category name and prevent duplicate names (case-insensitive & whitespace trimmed).
    """
    errors = []
    category_name = data.get('category_name', '').strip()

    if not category_name:
        errors.append("Category name is required and cannot be blank.")
    elif len(category_name) > 100:
        errors.append("Category name cannot exceed 100 characters.")
    else:
        # Check uniqueness case-insensitively and with trimmed whitespace
        check_sql = "SELECT category_id FROM categories WHERE LOWER(TRIM(category_name)) = LOWER(TRIM(%s))"
        params = [category_name]
        if existing_category_id:
            check_sql += " AND category_id != %s"
            params.append(existing_category_id)

        existing = query_db(check_sql, tuple(params), one=True)
        if existing:
            errors.append(f"A category named '{category_name}' already exists. Category names must be unique.")

    if errors:
        raise ValidationError("; ".join(errors))

def create_category(category_data):
    """Create a new category in the database."""
    validate_category_data(category_data)
    category_name = category_data['category_name'].strip()
    description = category_data.get('description', '').strip() or None
    status = category_data.get('status', 'ACTIVE')

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            INSERT INTO categories (category_name, description, status)
            VALUES (%s, %s, %s)
        """, (category_name, description, status))
        return cursor.lastrowid

def update_category(category_id, category_data):
    """Update an existing category's name, description, and status."""
    category = get_category_by_id(category_id, include_counts=False)
    if not category:
        raise ValidationError("Category not found.")

    validate_category_data(category_data, existing_category_id=category_id)
    category_name = category_data['category_name'].strip()
    description = category_data.get('description', '').strip() or None
    status = category_data.get('status', category['status'])

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE categories
            SET category_name = %s,
                description = %s,
                status = %s
            WHERE category_id = %s
        """, (category_name, description, status, category_id))
        return cursor.rowcount > 0

def toggle_category_status(category_id, new_status=None):
    """
    Safely toggle or set category status (ACTIVE / INACTIVE).
    Never deletes the category or its referencing products.
    """
    category = get_category_by_id(category_id, include_counts=False)
    if not category:
        raise ValidationError("Category not found.")

    if not new_status:
        new_status = 'INACTIVE' if category['status'] == 'ACTIVE' else 'ACTIVE'

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE categories
            SET status = %s
            WHERE category_id = %s
        """, (new_status, category_id))
        return new_status

def delete_category(category_id):
    """
    Performs safe deactivation of a category to protect referential integrity with products.
    """
    return toggle_category_status(category_id, new_status='INACTIVE')
