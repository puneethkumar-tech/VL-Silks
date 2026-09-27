import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.credit_service')

ALLOWED_PAYMENT_METHODS = ('CASH', 'UPI', 'CARD', 'BANK_TRANSFER')


class ValidationError(Exception):
    """Custom exception for credit/Udhaar validation errors."""
    pass


def to_decimal(val, default=Decimal('0.00')):
    """Safely convert a value to Decimal with 2 decimal places."""
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"Invalid monetary or numeric amount: {val}")


# ---------------------------------------------------------------------------
# 1. READ — Balance Calculations & Summaries
# ---------------------------------------------------------------------------

def calculate_customer_outstanding_balance(customer_id):
    """
    Calculate the authoritative outstanding Udhaar balance for a customer
    from the credit_transactions table.
    Outstanding Balance = Total CREDIT_SALE charges - Total (PAYMENT + RETURN_REFUND settlements).
    """
    if not customer_id:
        return Decimal('0.00')

    try:
        c_id = int(customer_id)
    except (ValueError, TypeError):
        return Decimal('0.00')

    sql = """
        SELECT COALESCE(SUM(CASE 
            WHEN transaction_type = 'CREDIT_SALE' THEN amount 
            WHEN transaction_type = 'PAYMENT' THEN -amount 
            WHEN transaction_type = 'RETURN_REFUND' THEN -amount 
            ELSE 0 
        END), 0.00) AS balance
        FROM credit_transactions
        WHERE customer_id = %s
    """
    row = query_db(sql, (c_id,), one=True)
    bal = to_decimal(row['balance']) if row else Decimal('0.00')
    return max(Decimal('0.00'), bal)


def get_customer_outstanding_balance(customer_id):
    """Alias for calculate_customer_outstanding_balance."""
    return calculate_customer_outstanding_balance(customer_id)


def calculate_total_credit_outstanding():
    """
    Calculate total outstanding credit to collect across all customers.
    """
    sql = """
        SELECT COALESCE(SUM(CASE 
            WHEN transaction_type = 'CREDIT_SALE' THEN amount 
            WHEN transaction_type = 'PAYMENT' THEN -amount 
            WHEN transaction_type = 'RETURN_REFUND' THEN -amount 
            ELSE 0 
        END), 0.00) AS total_outstanding
        FROM credit_transactions
    """
    row = query_db(sql, one=True)
    return to_decimal(row['total_outstanding']) if row else Decimal('0.00')


def get_credit_summary():
    """
    Generate high-level credit & Udhaar management metrics from actual DB records.
    Returns:
      - total_credit_customers (count of customers with outstanding > 0)
      - total_credit_to_collect (sum of outstanding balances)
      - total_credit_sales_amount
      - total_settlements_amount
      - total_credit_sales_count
      - total_settlements_count
    """
    # 1. Outstanding total & count of customers with positive balance
    cust_sql = """
        SELECT 
            c.customer_id,
            COALESCE(SUM(CASE 
                WHEN ct.transaction_type = 'CREDIT_SALE' THEN ct.amount 
                WHEN ct.transaction_type = 'PAYMENT' THEN -ct.amount 
                WHEN ct.transaction_type = 'RETURN_REFUND' THEN -ct.amount 
                ELSE 0 
            END), 0.00) AS outstanding
        FROM customers c
        JOIN credit_transactions ct ON c.customer_id = ct.customer_id
        GROUP BY c.customer_id
        HAVING outstanding > 0
    """
    active_credit_rows = query_db(cust_sql) or []
    total_credit_customers = len(active_credit_rows)
    total_credit_to_collect = sum((to_decimal(r['outstanding']) for r in active_credit_rows), Decimal('0.00'))

    # 2. Transaction aggregates
    tx_sql = """
        SELECT 
            COUNT(CASE WHEN transaction_type = 'CREDIT_SALE' THEN 1 END) AS credit_sales_count,
            COALESCE(SUM(CASE WHEN transaction_type = 'CREDIT_SALE' THEN amount ELSE 0 END), 0.00) AS credit_sales_amount,
            COUNT(CASE WHEN transaction_type = 'PAYMENT' THEN 1 END) AS settlements_count,
            COALESCE(SUM(CASE WHEN transaction_type = 'PAYMENT' THEN amount ELSE 0 END), 0.00) AS settlements_amount
        FROM credit_transactions
    """
    tx_data = query_db(tx_sql, one=True) or {}

    return {
        'total_credit_customers': total_credit_customers,
        'total_credit_to_collect': total_credit_to_collect,
        'total_credit_sales_amount': to_decimal(tx_data.get('credit_sales_amount', Decimal('0.00'))),
        'total_settlements_amount': to_decimal(tx_data.get('settlements_amount', Decimal('0.00'))),
        'total_credit_sales_count': tx_data.get('credit_sales_count', 0) or 0,
        'total_settlements_count': tx_data.get('settlements_count', 0) or 0,
    }


def get_credit_customers(search=None, status=None, min_balance=None):
    """
    Retrieve customers with credit records, their calculated outstanding balance,
    and available credit.
    Default filter includes customers with outstanding_balance > 0.
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
            COALESCE(SUM(CASE 
                WHEN ct.transaction_type = 'CREDIT_SALE' THEN ct.amount 
                WHEN ct.transaction_type = 'PAYMENT' THEN -ct.amount 
                WHEN ct.transaction_type = 'RETURN_REFUND' THEN -ct.amount 
                ELSE 0 
            END), 0.00) AS outstanding_balance,
            COUNT(ct.transaction_id) AS transaction_count,
            MAX(ct.transaction_date) AS last_transaction_date
        FROM customers c
        JOIN credit_transactions ct ON c.customer_id = ct.customer_id
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

    sql += " GROUP BY c.customer_id, c.customer_name, c.phone, c.email, c.address, c.credit_limit, c.status"

    if min_balance is not None:
        try:
            min_bal_dec = to_decimal(min_balance)
            sql += " HAVING outstanding_balance >= %s"
            params.append(min_bal_dec)
        except ValidationError:
            sql += " HAVING outstanding_balance > 0"
    else:
        sql += " HAVING outstanding_balance > 0"

    sql += " ORDER BY outstanding_balance DESC, c.customer_name ASC"

    rows = query_db(sql, tuple(params) if params else None) or []
    results = []
    for r in rows:
        item = dict(r)
        credit_limit = to_decimal(item.get('credit_limit', Decimal('25000.00')))
        outstanding = to_decimal(item.get('outstanding_balance', Decimal('0.00')))
        item['outstanding_balance'] = outstanding
        item['available_credit'] = max(Decimal('0.00'), credit_limit - outstanding)
        results.append(item)
    return results


def get_customer_credit_profile(customer_id):
    """
    Fetch comprehensive credit profile for a single customer.
    """
    if not customer_id:
        return None

    try:
        c_id = int(customer_id)
    except (ValueError, TypeError):
        return None

    customer = query_db(
        "SELECT customer_id, customer_name, phone, email, address, credit_limit, status, created_at, updated_at "
        "FROM customers WHERE customer_id = %s",
        (c_id,),
        one=True
    )
    if not customer:
        return None

    profile = dict(customer)
    credit_limit = to_decimal(profile.get('credit_limit', Decimal('25000.00')))

    # Financial aggregates from credit_transactions
    agg_sql = """
        SELECT 
            COUNT(CASE WHEN transaction_type = 'CREDIT_SALE' THEN 1 END) AS credit_sales_count,
            COALESCE(SUM(CASE WHEN transaction_type = 'CREDIT_SALE' THEN amount ELSE 0 END), 0.00) AS total_credit_amount,
            COUNT(CASE WHEN transaction_type = 'PAYMENT' THEN 1 END) AS settlements_count,
            COALESCE(SUM(CASE WHEN transaction_type = 'PAYMENT' THEN amount ELSE 0 END), 0.00) AS total_paid_amount,
            MAX(transaction_date) AS last_transaction_date
        FROM credit_transactions
        WHERE customer_id = %s
    """
    agg = query_db(agg_sql, (c_id,), one=True) or {}

    total_credit = to_decimal(agg.get('total_credit_amount', Decimal('0.00')))
    total_paid = to_decimal(agg.get('total_paid_amount', Decimal('0.00')))
    outstanding = max(Decimal('0.00'), total_credit - total_paid)
    available = max(Decimal('0.00'), credit_limit - outstanding)

    profile['credit_limit'] = credit_limit
    profile['total_credit_sales_count'] = agg.get('credit_sales_count', 0) or 0
    profile['total_credit_amount'] = total_credit
    profile['settlements_count'] = agg.get('settlements_count', 0) or 0
    profile['total_paid_amount'] = total_paid
    profile['outstanding_balance'] = outstanding
    profile['available_credit'] = available
    profile['last_transaction_date'] = agg.get('last_transaction_date')

    return profile


def get_customer_credit_history(customer_id):
    """
    Retrieve chronological credit transaction ledger for a customer with
    deterministic running balances.
    Ordered by transaction_date ASC, transaction_id ASC.
    """
    if not customer_id:
        return []

    try:
        c_id = int(customer_id)
    except (ValueError, TypeError):
        return []

    sql = """
        SELECT 
            ct.transaction_id,
            ct.customer_id,
            ct.sale_id,
            ct.payment_id,
            ct.transaction_type,
            ct.amount,
            ct.transaction_date,
            ct.notes,
            ct.created_at,
            ct.created_by,
            u.name AS created_by_name,
            s.invoice_number,
            p.payment_method,
            p.reference_number
        FROM credit_transactions ct
        JOIN users u ON ct.created_by = u.user_id
        LEFT JOIN sales s ON ct.sale_id = s.sale_id
        LEFT JOIN payments p ON ct.payment_id = p.payment_id
        WHERE ct.customer_id = %s
        ORDER BY ct.transaction_date ASC, ct.transaction_id ASC
    """
    rows = query_db(sql, (c_id,)) or []

    ledger = []
    running_balance = Decimal('0.00')

    for row in rows:
        item = dict(row)
        amt = to_decimal(item['amount'])
        ttype = item['transaction_type']

        if ttype == 'CREDIT_SALE':
            debit = amt
            credit = Decimal('0.00')
            running_balance += amt
        elif ttype in ('PAYMENT', 'RETURN_REFUND'):
            debit = Decimal('0.00')
            credit = amt
            running_balance -= amt
        else:  # ADJUSTMENT
            debit = amt
            credit = Decimal('0.00')
            running_balance += amt

        item['debit_amount'] = debit
        item['credit_amount'] = credit
        item['running_balance'] = running_balance.quantize(Decimal('0.01'))
        ledger.append(item)

    return ledger


# ---------------------------------------------------------------------------
# 2. WRITE — Atomic Credit Settlement Payment
# ---------------------------------------------------------------------------

def validate_settlement_data(customer_id, payment_data):
    """
    Validate settlement payment data against business invariants.
    """
    if not customer_id:
        raise ValidationError("Customer ID is required.")

    customer = query_db(
        "SELECT customer_id, customer_name, status, credit_limit FROM customers WHERE customer_id = %s",
        (customer_id,),
        one=True
    )
    if not customer:
        raise ValidationError(f"Customer #{customer_id} does not exist.")

    # Amount validation
    amount_raw = payment_data.get('amount')
    if amount_raw is None or str(amount_raw).strip() == '':
        raise ValidationError("Payment amount is required.")

    try:
        amount = to_decimal(amount_raw)
    except ValidationError:
        raise ValidationError("Payment amount must be a valid positive number.")

    if amount <= Decimal('0.00'):
        raise ValidationError(f"Payment amount must be greater than zero. Received: Rs.{amount:,.2f}")

    # Outstanding balance validation
    current_outstanding = calculate_customer_outstanding_balance(customer_id)
    if current_outstanding <= Decimal('0.00'):
        raise ValidationError(
            f"Customer '{customer['customer_name']}' has no outstanding balance (Balance: Rs.0.00)."
        )

    if amount > current_outstanding:
        raise ValidationError(
            f"Payment amount (Rs.{amount:,.2f}) cannot exceed customer's outstanding balance (Rs.{current_outstanding:,.2f})."
        )

    # Payment Method validation
    method = (payment_data.get('payment_method') or 'CASH').strip().upper()
    if method not in ALLOWED_PAYMENT_METHODS:
        raise ValidationError(
            f"Invalid payment method '{method}'. Allowed: {', '.join(ALLOWED_PAYMENT_METHODS)}."
        )

    # Payment Date validation
    date_raw = payment_data.get('payment_date')
    if not date_raw:
        payment_date = date.today()
    elif isinstance(date_raw, str):
        try:
            payment_date = datetime.strptime(date_raw.strip(), '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError("Invalid payment date format. Use YYYY-MM-DD.")
    elif isinstance(date_raw, (date, datetime)):
        payment_date = date_raw if isinstance(date_raw, date) else date_raw.date()
    else:
        raise ValidationError("Invalid payment date.")

    ref_num = (payment_data.get('reference_number') or '').strip() or None
    if ref_num and len(ref_num) > 100:
        raise ValidationError("Reference number cannot exceed 100 characters.")

    notes = (payment_data.get('notes') or '').strip() or None

    return {
        'customer': customer,
        'amount': amount,
        'payment_method': method,
        'payment_date': payment_date,
        'reference_number': ref_num,
        'notes': notes,
        'current_outstanding': current_outstanding,
    }


def record_credit_payment(customer_id, payment_data, user_id):
    """
    Atomically record a settlement payment against a customer's outstanding Udhaar.
    1. Locks and verifies current balance.
    2. Inserts payment into `payments` table.
    3. Inserts transaction into `credit_transactions` table with updated running balance.
    4. Rolls back on any error.
    Returns:
      {
        'payment_id': int,
        'transaction_id': int,
        'previous_balance': Decimal,
        'paid_amount': Decimal,
        'new_balance': Decimal
      }
    """
    if not user_id:
        raise ValidationError("User ID is required to record a settlement payment.")

    validated = validate_settlement_data(customer_id, payment_data)
    amount = validated['amount']
    pay_date = validated['payment_date']
    method = validated['payment_method']
    ref_num = validated['reference_number']
    notes = validated['notes']
    customer_name = validated['customer']['customer_name']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Re-verify and lock customer record to prevent race conditions
        cursor.execute("SELECT customer_id FROM customers WHERE customer_id = %s FOR UPDATE", (customer_id,))
        locked = cursor.fetchone()
        if not locked:
            raise ValidationError(f"Customer #{customer_id} not found during lock.")

        # Re-calculate outstanding inside transaction
        cursor.execute("""
            SELECT COALESCE(SUM(CASE 
                WHEN transaction_type = 'CREDIT_SALE' THEN amount 
                WHEN transaction_type = 'PAYMENT' THEN -amount 
                WHEN transaction_type = 'RETURN_REFUND' THEN -amount 
                ELSE 0 
            END), 0.00) AS balance
            FROM credit_transactions
            WHERE customer_id = %s
        """, (customer_id,))
        bal_row = cursor.fetchone()
        curr_bal = to_decimal(bal_row['balance'] if bal_row else Decimal('0.00'))

        if amount > curr_bal:
            raise ValidationError(
                f"Payment amount (Rs.{amount:,.2f}) exceeds current outstanding balance (Rs.{curr_bal:,.2f})."
            )

        new_balance = (curr_bal - amount).quantize(Decimal('0.01'))

        # 1. Insert into payments
        payment_notes = notes or f"Credit / Udhaar settlement for {customer_name}"
        cursor.execute("""
            INSERT INTO payments (
                customer_id, sale_id, amount, payment_method,
                payment_date, reference_number, notes, created_by
            ) VALUES (%s, NULL, %s, %s, %s, %s, %s, %s)
        """, (
            customer_id,
            amount,
            method,
            pay_date,
            ref_num,
            payment_notes,
            user_id
        ))
        payment_id = cursor.lastrowid

        # 2. Insert into credit_transactions
        # Build tx_notes to include reference number in audit trail
        if notes and ref_num:
            tx_notes = f"{notes} [Ref: {ref_num}]"
        elif notes:
            tx_notes = notes
        elif ref_num:
            tx_notes = f"Settlement payment #{payment_id} received via {method} [Ref: {ref_num}]"
        else:
            tx_notes = f"Settlement payment #{payment_id} received via {method}"

        cursor.execute("""
            INSERT INTO credit_transactions (
                customer_id, sale_id, payment_id,
                transaction_type, amount, running_balance,
                transaction_date, notes, created_by
            ) VALUES (%s, NULL, %s, 'PAYMENT', %s, %s, %s, %s, %s)
        """, (
            customer_id,
            payment_id,
            amount,
            new_balance,
            pay_date,
            tx_notes,
            user_id
        ))
        transaction_id = cursor.lastrowid

        conn.commit()
        logger.info(
            f"Credit settlement recorded successfully: Customer #{customer_id} ({customer_name}), "
            f"Paid: Rs.{amount}, Previous: Rs.{curr_bal}, New Balance: Rs.{new_balance}"
        )

        return {
            'payment_id': payment_id,
            'transaction_id': transaction_id,
            'customer_id': customer_id,
            'customer_name': customer_name,
            'previous_balance': curr_bal,
            'paid_amount': amount,
            'new_balance': new_balance,
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Error recording credit payment for customer #{customer_id}: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to record settlement payment: {str(e)}")
    finally:
        cursor.close()
        conn.close()
