import re
import logging
from decimal import Decimal, InvalidOperation
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.customer_service')

ALLOWED_STATUSES = ('ACTIVE', 'INACTIVE')
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')


class ValidationError(Exception):
    """Custom exception for customer business validation errors."""
    pass


def to_decimal(val, default=Decimal('0.00')):
    """Safely convert a value to Decimal with 2 decimal places."""
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"Invalid monetary or numeric amount: {val}")


# ---------------------------------------------------------------------------
# READ — List / Search / Get
# ---------------------------------------------------------------------------

def get_customers(search=None, status=None):
    """
    Fetch all customers with aggregated purchase statistics.
    Uses subquery aggregation on the sales table to avoid double-counting.
    Supports filtering by search (name / phone / email) and status (ACTIVE / INACTIVE).
    """
    sql = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.phone,
            c.email,
            c.address,
            c.credit_limit,
            c.status,
            c.created_at,
            c.updated_at,
            COALESCE(s_stat.invoice_count, 0) AS total_purchases,
            COALESCE(s_stat.total_purchased, 0.00) AS total_purchase_value,
            COALESCE(s_stat.total_paid, 0.00) AS total_paid,
            COALESCE(s_stat.outstanding, 0.00) AS outstanding_balance
        FROM customers c
        LEFT JOIN (
            SELECT
                customer_id,
                COUNT(*) AS invoice_count,
                SUM(total_amount) AS total_purchased,
                SUM(paid_amount) AS total_paid,
                SUM(balance_amount) AS outstanding
            FROM sales
            GROUP BY customer_id
        ) s_stat ON c.customer_id = s_stat.customer_id
        WHERE 1=1
    """
    params = []

    if status and status.upper() != 'ALL':
        sql += " AND c.status = %s"
        params.append(status.upper())

    if search and search.strip():
        term = f"%{search.strip()}%"
        sql += " AND (c.customer_name LIKE %s OR c.phone LIKE %s OR c.email LIKE %s)"
        params.extend([term, term, term])

    sql += " ORDER BY c.customer_name ASC"
    return query_db(sql, tuple(params) if params else None)


def get_customer_summary_metrics():
    """
    Calculate high-level customer directory metrics from the database.
    """
    total_sql = "SELECT COUNT(*) AS total_customers FROM customers"
    total_data = query_db(total_sql, one=True) or {}

    active_sql = "SELECT COUNT(*) AS active_customers FROM customers WHERE status = 'ACTIVE'"
    active_data = query_db(active_sql, one=True) or {}

    balance_sql = """
        SELECT
            COUNT(DISTINCT customer_id) AS customers_with_balance,
            COALESCE(SUM(balance_amount), 0.00) AS total_outstanding
        FROM sales
        WHERE customer_id IS NOT NULL AND balance_amount > 0
    """
    balance_data = query_db(balance_sql, one=True) or {}

    return {
        'total_customers': total_data.get('total_customers', 0) or 0,
        'active_customers': active_data.get('active_customers', 0) or 0,
        'customers_with_balance': balance_data.get('customers_with_balance', 0) or 0,
        'total_outstanding': to_decimal(balance_data.get('total_outstanding', Decimal('0.00'))),
    }


def get_customer_by_id(customer_id):
    """
    Fetch a single customer by ID with complete purchase statistics.
    """
    if not customer_id:
        return None

    try:
        c_id = int(customer_id)
    except (ValueError, TypeError):
        return None

    sql = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.phone,
            c.email,
            c.address,
            c.credit_limit,
            c.status,
            c.created_at,
            c.updated_at,
            COALESCE(s_stat.invoice_count, 0) AS total_purchases,
            COALESCE(s_stat.total_purchased, 0.00) AS total_purchase_value,
            COALESCE(s_stat.total_paid, 0.00) AS total_paid,
            COALESCE(s_stat.outstanding, 0.00) AS outstanding_balance
        FROM customers c
        LEFT JOIN (
            SELECT
                customer_id,
                COUNT(*) AS invoice_count,
                SUM(total_amount) AS total_purchased,
                SUM(paid_amount) AS total_paid,
                SUM(balance_amount) AS outstanding
            FROM sales
            GROUP BY customer_id
        ) s_stat ON c.customer_id = s_stat.customer_id
        WHERE c.customer_id = %s
    """
    customer = query_db(sql, (c_id,), one=True)
    if customer:
        credit_limit = to_decimal(customer.get('credit_limit', Decimal('25000.00')))
        outstanding = to_decimal(customer.get('outstanding_balance', Decimal('0.00')))
        customer['available_credit'] = max(Decimal('0.00'), credit_limit - outstanding)
    return customer


def get_customer_purchase_history(customer_id):
    """
    Fetch all sales invoices belonging to a customer with line item counts.
    """
    if not customer_id:
        return []

    try:
        c_id = int(customer_id)
    except (ValueError, TypeError):
        return []

    sql = """
        SELECT
            s.sale_id,
            s.invoice_number,
            s.sale_date,
            s.subtotal,
            s.discount,
            s.tax,
            s.total_amount,
            s.paid_amount,
            s.balance_amount,
            s.payment_method,
            s.payment_status,
            s.notes,
            s.created_at,
            s.created_by,
            u.name AS created_by_name,
            COUNT(si.sale_item_id) AS item_count,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM sales s
        JOIN users u ON s.created_by = u.user_id
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE s.customer_id = %s
        GROUP BY s.sale_id, u.user_id
        ORDER BY s.sale_date DESC, s.sale_id DESC
    """
    return query_db(sql, (c_id,))


def get_active_customers(search=None):
    """
    Fetch active customers for POS live customer search and dropdowns,
    including current outstanding balance and available credit limit.
    """
    sql = """
        SELECT
            c.customer_id,
            c.customer_name,
            c.phone,
            c.email,
            c.credit_limit,
            COALESCE(SUM(s.balance_amount), 0) AS current_balance,
            GREATEST(0, c.credit_limit - COALESCE(SUM(s.balance_amount), 0)) AS available_credit
        FROM customers c
        LEFT JOIN sales s ON c.customer_id = s.customer_id AND s.payment_status IN ('PARTIAL', 'CREDIT')
        WHERE c.status = 'ACTIVE'
    """
    params = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        sql += " AND (c.customer_name LIKE %s OR c.phone LIKE %s OR c.email LIKE %s)"
        params.extend([term, term, term])

    sql += """
        GROUP BY c.customer_id
        ORDER BY c.customer_name ASC
    """
    return query_db(sql, tuple(params) if params else None)


# ---------------------------------------------------------------------------
# WRITE — Create / Update / Status / Safe Deactivation
# ---------------------------------------------------------------------------

def validate_customer_data(data, existing_customer_id=None):
    """
    Validate customer data fields and phone uniqueness.
    """
    customer_name = (data.get('customer_name') or '').strip()
    if not customer_name:
        raise ValidationError("Customer name is required.")
    if len(customer_name) > 150:
        raise ValidationError("Customer name cannot exceed 150 characters.")

    phone = (data.get('phone') or '').strip()
    if not phone:
        raise ValidationError("Customer phone number is required.")
    if len(phone) > 20:
        raise ValidationError("Phone number cannot exceed 20 characters.")

    # Phone uniqueness check
    if existing_customer_id:
        dup = query_db(
            "SELECT customer_id FROM customers WHERE phone = %s AND customer_id != %s",
            (phone, existing_customer_id),
            one=True
        )
    else:
        dup = query_db(
            "SELECT customer_id FROM customers WHERE phone = %s",
            (phone,),
            one=True
        )
    if dup:
        raise ValidationError(f"A customer with phone number '{phone}' already exists.")

    email = (data.get('email') or '').strip() or None
    if email:
        if len(email) > 100:
            raise ValidationError("Email cannot exceed 100 characters.")
        if not EMAIL_REGEX.match(email):
            raise ValidationError("Invalid email address format.")

    address = (data.get('address') or '').strip() or None

    credit_limit_raw = data.get('credit_limit', 25000.00)
    try:
        credit_limit = to_decimal(credit_limit_raw, default=Decimal('25000.00'))
    except ValidationError:
        raise ValidationError("Credit limit must be a valid number.")
    if credit_limit < Decimal('0.00'):
        raise ValidationError("Credit limit cannot be negative.")

    status = (data.get('status') or 'ACTIVE').strip().upper()
    if status not in ALLOWED_STATUSES:
        raise ValidationError(f"Invalid status '{status}'. Allowed: {', '.join(ALLOWED_STATUSES)}.")

    return {
        'customer_name': customer_name,
        'phone': phone,
        'email': email,
        'address': address,
        'credit_limit': credit_limit,
        'status': status,
    }


def create_customer(data):
    """
    Create a new customer with validation.
    """
    validated = validate_customer_data(data)

    sql = """
        INSERT INTO customers (customer_name, phone, email, address, credit_limit, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            validated['customer_name'],
            validated['phone'],
            validated['email'],
            validated['address'],
            validated['credit_limit'],
            validated['status'],
        ))
        conn.commit()
        cust_id = cursor.lastrowid
        cursor.close()
        logger.info(f"Customer #{cust_id} ('{validated['customer_name']}') created successfully.")
        return cust_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating customer: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to create customer: {str(e)}")
    finally:
        conn.close()


def update_customer(customer_id, data):
    """
    Update an existing customer's details with validation.
    Does NOT modify historical sales, payments, or credit transactions.
    """
    if not customer_id:
        raise ValidationError("Customer ID is required.")

    existing = query_db("SELECT * FROM customers WHERE customer_id = %s", (customer_id,), one=True)
    if not existing:
        raise ValidationError("Customer not found.")

    validated = validate_customer_data(data, existing_customer_id=customer_id)

    sql = """
        UPDATE customers
        SET customer_name = %s,
            phone = %s,
            email = %s,
            address = %s,
            credit_limit = %s,
            status = %s
        WHERE customer_id = %s
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            validated['customer_name'],
            validated['phone'],
            validated['email'],
            validated['address'],
            validated['credit_limit'],
            validated['status'],
            customer_id,
        ))
        conn.commit()
        cursor.close()
        logger.info(f"Customer #{customer_id} updated successfully.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating customer #{customer_id}: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to update customer: {str(e)}")
    finally:
        conn.close()


def toggle_customer_status(customer_id):
    """
    Safely toggle active/inactive status of a customer.
    Historical sales and credit records remain completely intact.
    """
    customer = query_db("SELECT customer_id, status FROM customers WHERE customer_id = %s", (customer_id,), one=True)
    if not customer:
        raise ValidationError("Customer not found.")

    new_status = 'INACTIVE' if customer['status'] == 'ACTIVE' else 'ACTIVE'
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE customers SET status = %s WHERE customer_id = %s", (new_status, customer_id))
        conn.commit()
        cursor.close()
        logger.info(f"Customer #{customer_id} status toggled to {new_status}.")
        return new_status
    except Exception as e:
        conn.rollback()
        logger.error(f"Error toggling status for customer #{customer_id}: {e}")
        raise ValidationError(f"Failed to update customer status: {str(e)}")
    finally:
        conn.close()


def delete_customer(customer_id):
    """
    Safe deactivation of a customer.
    Never physically deletes a customer record or destroys historical sales/payments/credit.
    Sets status to INACTIVE.
    """
    customer = query_db("SELECT customer_id, status FROM customers WHERE customer_id = %s", (customer_id,), one=True)
    if not customer:
        raise ValidationError("Customer not found.")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE customers SET status = 'INACTIVE' WHERE customer_id = %s", (customer_id,))
        conn.commit()
        cursor.close()
        logger.info(f"Customer #{customer_id} safely deactivated.")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Error deactivating customer #{customer_id}: {e}")
        raise ValidationError(f"Failed to deactivate customer: {str(e)}")
    finally:
        conn.close()


def quick_create_customer(customer_name, phone, credit_limit=25000.0, email=None, address=None):
    """
    Quickly register a new customer from the POS checkout flow.
    """
    return create_customer({
        'customer_name': customer_name,
        'phone': phone,
        'credit_limit': credit_limit,
        'email': email,
        'address': address,
        'status': 'ACTIVE',
    })
