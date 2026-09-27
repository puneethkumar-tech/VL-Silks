import logging
from backend.utils.database import get_db_cursor, query_db

logger = logging.getLogger('vl_silks.supplier_service')


class ValidationError(Exception):
    """Custom exception for supplier business validation errors."""
    pass


def get_all_suppliers(search=None, status=None):
    """
    Fetch all suppliers with aggregated purchase count and total purchase value.
    Supports search across supplier_name, contact_person, phone, and email.
    """
    sql = """
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.contact_person,
            s.phone,
            s.email,
            s.address,
            s.gst_number,
            s.status,
            s.created_at,
            s.updated_at,
            COUNT(p.purchase_id) AS purchase_count,
            COALESCE(SUM(p.total), 0) AS total_purchase_value
        FROM suppliers s
        LEFT JOIN purchases p ON s.supplier_id = p.supplier_id
        WHERE 1=1
    """
    params = []

    if status and status.upper() != 'ALL':
        sql += " AND s.status = %s"
        params.append(status.upper())

    if search:
        search_term = f"%{search.strip()}%"
        sql += """ AND (
            s.supplier_name LIKE %s OR
            s.contact_person LIKE %s OR
            s.phone LIKE %s OR
            s.email LIKE %s
        )"""
        params.extend([search_term, search_term, search_term, search_term])

    sql += " GROUP BY s.supplier_id ORDER BY s.supplier_name ASC"
    return query_db(sql, tuple(params))


def get_supplier_by_id(supplier_id):
    """Fetch a single supplier by ID with purchase count and total value."""
    sql = """
        SELECT
            s.supplier_id,
            s.supplier_name,
            s.contact_person,
            s.phone,
            s.email,
            s.address,
            s.gst_number,
            s.status,
            s.created_at,
            s.updated_at,
            COUNT(p.purchase_id) AS purchase_count,
            COALESCE(SUM(p.total), 0) AS total_purchase_value
        FROM suppliers s
        LEFT JOIN purchases p ON s.supplier_id = p.supplier_id
        WHERE s.supplier_id = %s
        GROUP BY s.supplier_id
    """
    return query_db(sql, (supplier_id,), one=True)


def get_supplier_purchase_history(supplier_id, limit=20):
    """
    Fetch paginated purchase history for a given supplier.
    Returns purchases in reverse chronological order with payment status.
    """
    sql = """
        SELECT
            p.purchase_id,
            p.invoice_number,
            p.purchase_date,
            p.subtotal,
            p.discount,
            p.tax,
            p.total,
            p.payment_status,
            p.notes,
            COUNT(pi.purchase_item_id) AS item_count
        FROM purchases p
        LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        WHERE p.supplier_id = %s
        GROUP BY p.purchase_id
        ORDER BY p.purchase_date DESC
        LIMIT %s
    """
    return query_db(sql, (supplier_id, limit))


def validate_supplier_data(data, existing_supplier_id=None):
    """
    Validate supplier fields:
    - supplier_name: required, max 150 chars
    - phone: required, max 20 chars
    - email: optional, basic format check
    - gst_number: optional, max 30 chars
    """
    errors = []

    supplier_name = data.get('supplier_name', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    gst_number = data.get('gst_number', '').strip()

    if not supplier_name:
        errors.append("Supplier name is required and cannot be blank.")
    elif len(supplier_name) > 150:
        errors.append("Supplier name cannot exceed 150 characters.")

    if not phone:
        errors.append("Phone number is required.")
    elif len(phone) > 20:
        errors.append("Phone number cannot exceed 20 characters.")

    if email and '@' not in email:
        errors.append("Email address does not appear to be valid.")
    elif len(email) > 100:
        errors.append("Email address cannot exceed 100 characters.")

    if gst_number and len(gst_number) > 30:
        errors.append("GST number cannot exceed 30 characters.")

    if errors:
        raise ValidationError("; ".join(errors))


def create_supplier(supplier_data):
    """Create a new supplier record in the database."""
    validate_supplier_data(supplier_data)

    supplier_name = supplier_data['supplier_name'].strip()
    contact_person = supplier_data.get('contact_person', '').strip() or None
    phone = supplier_data['phone'].strip()
    email = supplier_data.get('email', '').strip() or None
    address = supplier_data.get('address', '').strip() or None
    gst_number = supplier_data.get('gst_number', '').strip() or None
    status = supplier_data.get('status', 'ACTIVE')

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            INSERT INTO suppliers
                (supplier_name, contact_person, phone, email, address, gst_number, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (supplier_name, contact_person, phone, email, address, gst_number, status))
        return cursor.lastrowid


def update_supplier(supplier_id, supplier_data):
    """Update an existing supplier's details."""
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise ValidationError("Supplier not found.")

    validate_supplier_data(supplier_data, existing_supplier_id=supplier_id)

    supplier_name = supplier_data['supplier_name'].strip()
    contact_person = supplier_data.get('contact_person', '').strip() or None
    phone = supplier_data['phone'].strip()
    email = supplier_data.get('email', '').strip() or None
    address = supplier_data.get('address', '').strip() or None
    gst_number = supplier_data.get('gst_number', '').strip() or None
    status = supplier_data.get('status', supplier['status'])

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE suppliers
            SET supplier_name = %s,
                contact_person = %s,
                phone = %s,
                email = %s,
                address = %s,
                gst_number = %s,
                status = %s
            WHERE supplier_id = %s
        """, (supplier_name, contact_person, phone, email, address, gst_number, status, supplier_id))
        return cursor.rowcount > 0


def toggle_supplier_status(supplier_id, new_status=None):
    """
    Safely toggle or set supplier status (ACTIVE / INACTIVE).
    Does not delete the supplier or its purchase history.
    """
    supplier = get_supplier_by_id(supplier_id)
    if not supplier:
        raise ValidationError("Supplier not found.")

    if not new_status:
        new_status = 'INACTIVE' if supplier['status'] == 'ACTIVE' else 'ACTIVE'

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("""
            UPDATE suppliers SET status = %s WHERE supplier_id = %s
        """, (new_status, supplier_id))
        return new_status


def delete_supplier(supplier_id):
    """
    Performs safe deactivation of a supplier.
    Preserves all historical purchase records.
    """
    return toggle_supplier_status(supplier_id, new_status='INACTIVE')
