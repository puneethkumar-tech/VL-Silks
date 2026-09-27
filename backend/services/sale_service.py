import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.sale_service')

ALLOWED_PAYMENT_METHODS = ('CASH', 'UPI', 'CARD', 'CREDIT', 'SPLIT')
ALLOWED_PAYMENT_STATUSES = ('PAID', 'PARTIAL', 'CREDIT')


class ValidationError(Exception):
    """Custom exception for sale business validation errors."""
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

def get_all_sales(search=None, payment_method=None, payment_status=None,
                  date_from=None, date_to=None):
    """
    Fetch all sales with customer info, item counts, and totals.
    Supports filtering by search (invoice / customer name), payment_method,
    payment_status, and date range.
    """
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
            c.customer_id,
            c.customer_name,
            c.phone AS customer_phone,
            COUNT(si.sale_item_id) AS item_count,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM sales s
        JOIN users u ON s.created_by = u.user_id
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE 1=1
    """
    params = []

    if payment_method and payment_method.upper() != 'ALL':
        sql += " AND s.payment_method = %s"
        params.append(payment_method.upper())

    if payment_status and payment_status.upper() != 'ALL':
        sql += " AND s.payment_status = %s"
        params.append(payment_status.upper())

    if date_from:
        sql += " AND s.sale_date >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND s.sale_date <= %s"
        params.append(date_to)

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (s.invoice_number LIKE %s OR c.customer_name LIKE %s OR c.phone LIKE %s)"
        params.extend([search_term, search_term, search_term])

    sql += """
        GROUP BY s.sale_id, u.user_id, c.customer_id
        ORDER BY s.sale_date DESC, s.sale_id DESC
    """
    return query_db(sql, tuple(params))


def get_sale_summary_metrics():
    """
    Calculate high-level sales metrics from the live database.
    """
    today = date.today()
    first_day_of_month = today.replace(day=1)

    all_time_sql = """
        SELECT
            COUNT(*) AS total_sales,
            COALESCE(SUM(total_amount), 0) AS total_revenue,
            COALESCE(SUM(balance_amount), 0) AS total_outstanding
        FROM sales
    """
    all_time = query_db(all_time_sql, one=True) or {}

    month_sql = """
        SELECT
            COUNT(*) AS this_month_count,
            COALESCE(SUM(total_amount), 0) AS this_month_revenue
        FROM sales
        WHERE sale_date >= %s AND sale_date <= %s
    """
    month_data = query_db(month_sql, (first_day_of_month, today), one=True) or {}

    credit_sql = """
        SELECT COUNT(*) AS credit_sales_count
        FROM sales
        WHERE payment_status IN ('PARTIAL', 'CREDIT')
    """
    credit_data = query_db(credit_sql, one=True) or {}

    return {
        'total_sales': all_time.get('total_sales', 0) or 0,
        'total_revenue': all_time.get('total_revenue', Decimal('0.00')) or Decimal('0.00'),
        'total_outstanding': all_time.get('total_outstanding', Decimal('0.00')) or Decimal('0.00'),
        'this_month_count': month_data.get('this_month_count', 0) or 0,
        'this_month_revenue': month_data.get('this_month_revenue', Decimal('0.00')) or Decimal('0.00'),
        'credit_sales_count': credit_data.get('credit_sales_count', 0) or 0,
    }


def get_sale_by_id(sale_id):
    """Fetch a single sale by ID with customer and user details."""
    sql = """
        SELECT
            s.sale_id,
            s.customer_id,
            c.customer_name,
            c.phone AS customer_phone,
            c.email AS customer_email,
            c.address AS customer_address,
            c.credit_limit,
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
            s.created_by,
            u.name AS created_by_name,
            s.created_at,
            s.updated_at,
            COUNT(si.sale_item_id) AS item_count,
            COALESCE(SUM(si.quantity), 0) AS total_quantity
        FROM sales s
        JOIN users u ON s.created_by = u.user_id
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE s.sale_id = %s
        GROUP BY s.sale_id, u.user_id, c.customer_id
    """
    return query_db(sql, (sale_id,), one=True)


def get_sale_items(sale_id):
    """Fetch all line items belonging to a sale with complete variant details."""
    sql = """
        SELECT
            si.sale_item_id,
            si.sale_id,
            si.variant_id,
            si.quantity,
            si.unit_price,
            si.discount,
            si.total_price,
            si.created_at,
            pv.sku,
            pv.size,
            pv.color,
            pv.stock_quantity AS current_stock,
            p.product_id,
            p.product_name,
            p.brand,
            p.material,
            cat.category_name
        FROM sale_items si
        JOIN product_variants pv ON si.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE si.sale_id = %s
        ORDER BY si.sale_item_id ASC
    """
    return query_db(sql, (sale_id,))


def get_active_variants_for_sale(search=None):
    """
    Fetch all active product variants belonging to active products with stock > 0.
    Includes product name, brand, category, SKU, size, color, current stock, and selling price.
    Supports optional search filter across name, SKU, brand, and barcode.
    """
    sql = """
        SELECT
            pv.variant_id,
            pv.product_id,
            p.product_name,
            p.brand,
            cat.category_name,
            pv.sku,
            pv.size,
            pv.color,
            pv.selling_price,
            pv.stock_quantity,
            pv.barcode
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE pv.status = 'ACTIVE' AND p.status = 'ACTIVE' AND pv.stock_quantity > 0
    """
    params = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        sql += " AND (p.product_name LIKE %s OR pv.sku LIKE %s OR p.brand LIKE %s OR pv.barcode LIKE %s)"
        params.extend([term, term, term, term])

    sql += " ORDER BY p.product_name ASC, pv.sku ASC"
    return query_db(sql, tuple(params) if params else None)


def get_active_customers(search=None):
    """
    Fetch active customers for the POS customer search / dropdown.
    Delegates to customer_service.
    """
    from backend.services import customer_service
    return customer_service.get_active_customers(search=search)


def quick_create_customer(customer_name, phone, credit_limit=25000.0, email=None, address=None):
    """
    Quickly register a new customer from the POS checkout flow.
    Delegates to customer_service.
    """
    from backend.services import customer_service
    return customer_service.quick_create_customer(
        customer_name=customer_name,
        phone=phone,
        credit_limit=credit_limit,
        email=email,
        address=address
    )


def get_customer_outstanding_balance(customer_id):
    """
    Calculate the current outstanding credit balance for a customer
    as the sum of balance_amount on unpaid/partial sales.
    """
    sql = """
        SELECT COALESCE(SUM(balance_amount), 0) AS outstanding
        FROM sales
        WHERE customer_id = %s AND payment_status IN ('PARTIAL', 'CREDIT')
    """
    row = query_db(sql, (customer_id,), one=True)
    return to_decimal(row['outstanding']) if row else Decimal('0.00')


def generate_invoice_number():
    """
    Generate the next unique invoice number in the format SALE-YYYY-NNNN.
    Guarantees collision resistance even after test deletions or concurrency.
    """
    today = date.today()
    year = today.year
    prefix = f"SALE-{year}-"
    sql = "SELECT invoice_number FROM sales WHERE invoice_number LIKE %s ORDER BY sale_id DESC LIMIT 100"
    rows = query_db(sql, (f"{prefix}%",)) or []
    max_seq = 0
    for r in rows:
        inv = r.get('invoice_number', '')
        if inv.startswith(prefix):
            suffix = inv[len(prefix):]
            if suffix.isdigit():
                max_seq = max(max_seq, int(suffix))

    sql_cnt = "SELECT COUNT(*) AS cnt FROM sales WHERE YEAR(sale_date) = %s"
    row = query_db(sql_cnt, (year,), one=True)
    count = (row['cnt'] if row else 0) or 0
    next_num = max(max_seq + 1, count + 1)

    while True:
        candidate = f"SALE-{year}-{next_num:04d}"
        exists = query_db("SELECT 1 FROM sales WHERE invoice_number = %s", (candidate,), one=True)
        if not exists:
            return candidate
        next_num += 1


# ---------------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------------

def validate_sale_data(sale_data, items_data):
    """
    Validate all header fields and line items before starting the DB transaction.
    Returns a dict of sanitised, calculated values ready for insertion.
    """
    # 1. Optional Customer Validation
    customer_id_raw = sale_data.get('customer_id')
    customer_id = None
    customer = None
    if customer_id_raw and str(customer_id_raw).strip():
        try:
            customer_id = int(customer_id_raw)
        except (ValueError, TypeError):
            raise ValidationError("Invalid customer ID.")
        customer = query_db(
            "SELECT customer_id, customer_name, status, credit_limit FROM customers WHERE customer_id = %s",
            (customer_id,), one=True
        )
        if not customer:
            raise ValidationError("Selected customer does not exist.")
        if customer['status'] != 'ACTIVE':
            raise ValidationError(
                f"Customer '{customer['customer_name']}' is inactive and cannot be billed."
            )

    # 2. Sale Date Validation
    sale_date_raw = sale_data.get('sale_date')
    if not sale_date_raw:
        raise ValidationError("Sale date is required.")
    if isinstance(sale_date_raw, str):
        try:
            sale_date = datetime.strptime(sale_date_raw.strip(), '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError("Invalid sale date format. Use YYYY-MM-DD.")
    elif isinstance(sale_date_raw, (date, datetime)):
        sale_date = sale_date_raw if isinstance(sale_date_raw, date) else sale_date_raw.date()
    else:
        raise ValidationError("Invalid sale date.")

    # 3. Payment Method Validation
    payment_method = (sale_data.get('payment_method') or 'CASH').strip().upper()
    if payment_method not in ALLOWED_PAYMENT_METHODS:
        raise ValidationError(
            f"Invalid payment method '{payment_method}'. Allowed: {', '.join(ALLOWED_PAYMENT_METHODS)}."
        )

    if payment_method in ('CREDIT', 'SPLIT') and not customer_id:
        raise ValidationError(
            f"A customer must be selected for '{payment_method}' payment method."
        )

    # 4. Discount and Tax Validation
    try:
        discount = to_decimal(sale_data.get('discount', '0.00'))
    except ValidationError:
        raise ValidationError("Discount must be a valid non-negative number.")
    if discount < Decimal('0.00'):
        raise ValidationError("Discount cannot be negative.")

    try:
        tax = to_decimal(sale_data.get('tax', '0.00'))
    except ValidationError:
        raise ValidationError("Tax must be a valid non-negative number.")
    if tax < Decimal('0.00'):
        raise ValidationError("Tax cannot be negative.")

    notes = (sale_data.get('notes') or '').strip() or None

    # 5. Items Validation
    if not items_data or len(items_data) == 0:
        raise ValidationError("A sale must contain at least one product variant item.")

    seen_variants = set()
    validated_items = []
    subtotal = Decimal('0.00')

    for idx, item in enumerate(items_data, start=1):
        variant_id_raw = item.get('variant_id')
        if not variant_id_raw:
            raise ValidationError(f"Row {idx}: Product variant is required.")
        try:
            variant_id = int(variant_id_raw)
        except (ValueError, TypeError):
            raise ValidationError(f"Row {idx}: Invalid variant ID.")

        if variant_id in seen_variants:
            raise ValidationError(
                f"Duplicate variant detected (Variant ID {variant_id}). "
                "Each variant can only appear once per sale. Combine quantities into one row."
            )
        seen_variants.add(variant_id)

        variant = query_db("""
            SELECT
                pv.variant_id,
                pv.sku,
                pv.size,
                pv.color,
                pv.status AS variant_status,
                pv.stock_quantity,
                pv.selling_price,
                p.product_name,
                p.status AS product_status
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.product_id
            WHERE pv.variant_id = %s
        """, (variant_id,), one=True)

        if not variant:
            raise ValidationError(f"Row {idx}: Variant ID {variant_id} does not exist.")
        if variant['product_status'] != 'ACTIVE':
            raise ValidationError(
                f"Row {idx}: Product '{variant['product_name']}' is inactive and cannot be sold."
            )
        if variant['variant_status'] != 'ACTIVE':
            raise ValidationError(
                f"Row {idx}: Variant SKU '{variant['sku']}' ({variant['product_name']}) "
                "is inactive and cannot be sold."
            )

        # Quantity
        quantity_raw = item.get('quantity')
        try:
            quantity = int(quantity_raw)
        except (ValueError, TypeError):
            raise ValidationError(f"Row {idx} ({variant['sku']}): Quantity must be a valid integer.")
        if quantity <= 0:
            raise ValidationError(
                f"Row {idx} ({variant['sku']}): Quantity must be greater than zero. Received: {quantity}."
            )

        # Pre-check stock (authoritative lock happens inside the transaction)
        if variant['stock_quantity'] < quantity:
            raise ValidationError(
                f"Row {idx} ({variant['sku']}): Insufficient stock. "
                f"Available: {variant['stock_quantity']}, Requested: {quantity}."
            )

        # Unit price
        unit_price_raw = item.get('unit_price')
        if unit_price_raw is not None and str(unit_price_raw).strip():
            try:
                unit_price = to_decimal(unit_price_raw)
            except ValidationError:
                raise ValidationError(f"Row {idx} ({variant['sku']}): Unit price must be a valid number.")
            if unit_price < Decimal('0.00'):
                raise ValidationError(
                    f"Row {idx} ({variant['sku']}): Unit price cannot be negative."
                )
        else:
            unit_price = to_decimal(variant['selling_price'])

        # Per-item discount
        item_discount_raw = item.get('item_discount', '0.00')
        try:
            item_discount = to_decimal(item_discount_raw)
        except ValidationError:
            raise ValidationError(f"Row {idx} ({variant['sku']}): Item discount must be a valid number.")
        if item_discount < Decimal('0.00'):
            raise ValidationError(f"Row {idx} ({variant['sku']}): Item discount cannot be negative.")

        line_total = (Decimal(quantity) * unit_price - item_discount).quantize(Decimal('0.01'))
        if line_total < Decimal('0.00'):
            raise ValidationError(
                f"Row {idx} ({variant['sku']}): Line total cannot be negative."
            )
        subtotal += line_total

        validated_items.append({
            'variant_id': variant_id,
            'sku': variant['sku'],
            'product_name': variant['product_name'],
            'quantity': quantity,
            'unit_price': unit_price.quantize(Decimal('0.01')),
            'item_discount': item_discount.quantize(Decimal('0.01')),
            'total_price': line_total,
            'current_stock': variant['stock_quantity'],
        })

    # 6. Header totals
    grand_total = (subtotal - discount + tax).quantize(Decimal('0.01'))
    if grand_total < Decimal('0.00'):
        raise ValidationError(
            f"Calculated grand total (Rs.{grand_total}) cannot be negative. "
            f"Discount (Rs.{discount}) exceeds subtotal + tax (Rs.{subtotal + tax})."
        )

    # 7. Paid amount
    paid_amount_raw = sale_data.get('paid_amount')
    if paid_amount_raw is not None and str(paid_amount_raw).strip():
        try:
            paid_amount = to_decimal(paid_amount_raw)
        except ValidationError:
            raise ValidationError("Paid amount must be a valid non-negative number.")
        if paid_amount < Decimal('0.00'):
            raise ValidationError("Paid amount cannot be negative.")
        if paid_amount > grand_total:
            raise ValidationError(
                f"Paid amount (Rs.{paid_amount}) cannot exceed grand total (Rs.{grand_total})."
            )
    else:
        paid_amount = Decimal('0.00') if payment_method == 'CREDIT' else grand_total

    balance_amount = (grand_total - paid_amount).quantize(Decimal('0.01'))

    # 8. Derive payment_status
    if balance_amount == Decimal('0.00'):
        payment_status = 'PAID'
    elif paid_amount == Decimal('0.00'):
        payment_status = 'CREDIT'
    else:
        payment_status = 'PARTIAL'

    # 9. Credit limit check for credit/partial sales
    if (customer and payment_status in ('CREDIT', 'PARTIAL')
            and balance_amount > Decimal('0.00')):
        outstanding = get_customer_outstanding_balance(customer_id)
        credit_limit = to_decimal(customer.get('credit_limit', '25000.00'))
        if (outstanding + balance_amount) > credit_limit:
            raise ValidationError(
                f"Customer '{customer['customer_name']}' credit limit "
                f"(Rs.{credit_limit:,.2f}) exceeded. "
                f"Current outstanding: Rs.{outstanding:,.2f}, "
                f"New credit: Rs.{balance_amount:,.2f}."
            )

    return {
        'customer_id': customer_id,
        'sale_date': sale_date,
        'payment_method': payment_method,
        'payment_status': payment_status,
        'discount': discount.quantize(Decimal('0.01')),
        'tax': tax.quantize(Decimal('0.01')),
        'notes': notes,
        'validated_items': validated_items,
        'subtotal': subtotal.quantize(Decimal('0.01')),
        'grand_total': grand_total,
        'paid_amount': paid_amount.quantize(Decimal('0.01')),
        'balance_amount': balance_amount.quantize(Decimal('0.01')),
    }


# ---------------------------------------------------------------------------
# WRITE — Atomic Create Sale
# ---------------------------------------------------------------------------

def create_sale(sale_data, items_data, user_id):
    """
    Atomically create a sale with line items, reduce stock (with FOR UPDATE lock),
    create audit stock_movements, create a credit_transaction for credit/partial
    sales, and record the initial payment if applicable.

    Rolls back the entire transaction on ANY failure.
    Returns the new sale_id.
    """
    validated = validate_sale_data(sale_data, items_data)

    if not user_id:
        raise ValidationError("User ID is required to create a sale record.")

    invoice_number = (sale_data.get('invoice_number') or '').strip()
    if not invoice_number:
        invoice_number = generate_invoice_number()
    if len(invoice_number) > 50:
        raise ValidationError("Invoice number cannot exceed 50 characters.")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # ---------------------------------------------------------------
        # 1. Re-check stock with row-level locks (FOR UPDATE)
        # ---------------------------------------------------------------
        for item in validated['validated_items']:
            cursor.execute(
                "SELECT stock_quantity FROM product_variants WHERE variant_id = %s FOR UPDATE",
                (item['variant_id'],)
            )
            locked = cursor.fetchone()
            if not locked:
                raise ValidationError(f"Variant ID {item['variant_id']} not found during stock lock.")
            if locked['stock_quantity'] < item['quantity']:
                raise ValidationError(
                    f"Insufficient stock for SKU '{item['sku']}'. "
                    f"Available: {locked['stock_quantity']}, Requested: {item['quantity']}."
                )

        # ---------------------------------------------------------------
        # 2. Insert Sale Header
        # ---------------------------------------------------------------
        cursor.execute("""
            INSERT INTO sales (
                customer_id, invoice_number, sale_date,
                subtotal, discount, tax, total_amount,
                paid_amount, balance_amount,
                payment_method, payment_status, notes, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            validated['customer_id'],
            invoice_number,
            validated['sale_date'],
            validated['subtotal'],
            validated['discount'],
            validated['tax'],
            validated['grand_total'],
            validated['paid_amount'],
            validated['balance_amount'],
            validated['payment_method'],
            validated['payment_status'],
            validated['notes'],
            user_id,
        ))
        sale_id = cursor.lastrowid

        # ---------------------------------------------------------------
        # 3. Process Line Items -> reduce stock -> audit movements
        # ---------------------------------------------------------------
        for item in validated['validated_items']:
            # 3a. Insert sale_item
            cursor.execute("""
                INSERT INTO sale_items (
                    sale_id, variant_id, quantity, unit_price, discount, total_price
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                sale_id,
                item['variant_id'],
                item['quantity'],
                item['unit_price'],
                item['item_discount'],
                item['total_price'],
            ))

            # 3b. Decrement stock
            cursor.execute("""
                UPDATE product_variants
                SET stock_quantity = stock_quantity - %s
                WHERE variant_id = %s AND stock_quantity >= %s
            """, (item['quantity'], item['variant_id'], item['quantity']))

            if cursor.rowcount == 0:
                raise ValidationError(
                    f"Stock update failed for SKU '{item['sku']}' - "
                    "concurrent update or insufficient stock."
                )

            # 3c. Stock movement audit (negative quantity = stock reduction)
            movement_notes = (
                f"Sale #{invoice_number} - {item['quantity']} unit(s) of {item['sku']} sold"
            )
            cursor.execute("""
                INSERT INTO stock_movements (
                    variant_id, movement_type, quantity,
                    reference_type, reference_id, notes, created_by
                ) VALUES (%s, 'SALE', %s, 'SALE', %s, %s, %s)
            """, (
                item['variant_id'],
                -item['quantity'],
                sale_id,
                movement_notes,
                user_id,
            ))

        # ---------------------------------------------------------------
        # 4. Create credit_transaction for credit / partial sales
        # ---------------------------------------------------------------
        if (validated['payment_status'] in ('CREDIT', 'PARTIAL')
                and validated['customer_id']
                and validated['balance_amount'] > Decimal('0.00')):

            running_bal = get_customer_outstanding_balance(validated['customer_id'])
            new_running_bal = (running_bal + validated['balance_amount']).quantize(Decimal('0.01'))

            cursor.execute("""
                INSERT INTO credit_transactions (
                    customer_id, sale_id, payment_id,
                    transaction_type, amount, running_balance,
                    transaction_date, notes, created_by
                ) VALUES (%s, %s, NULL, 'CREDIT_SALE', %s, %s, %s, %s, %s)
            """, (
                validated['customer_id'],
                sale_id,
                validated['balance_amount'],
                new_running_bal,
                validated['sale_date'],
                f"Credit sale - Invoice {invoice_number}",
                user_id,
            ))

        # ---------------------------------------------------------------
        # 5. Record initial payment if paid_amount > 0 and customer linked
        # ---------------------------------------------------------------
        if (validated['paid_amount'] > Decimal('0.00')
                and validated['customer_id']
                and validated['payment_method'] not in ('CREDIT',)):

            pm_map = {'CASH': 'CASH', 'UPI': 'UPI', 'CARD': 'CARD', 'SPLIT': 'CASH'}
            pay_method = pm_map.get(validated['payment_method'], 'CASH')

            cursor.execute("""
                INSERT INTO payments (
                    customer_id, sale_id, amount, payment_method,
                    payment_date, reference_number, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, NULL, %s, %s)
            """, (
                validated['customer_id'],
                sale_id,
                validated['paid_amount'],
                pay_method,
                validated['sale_date'],
                f"Payment for Invoice {invoice_number}",
                user_id,
            ))

        # ---------------------------------------------------------------
        # 6. Commit
        # ---------------------------------------------------------------
        connection.commit()
        logger.info(
            f"Sale #{sale_id} (Invoice: {invoice_number}) created successfully "
            f"with {len(validated['validated_items'])} items. "
            f"Status: {validated['payment_status']}, Total: {validated['grand_total']}"
        )
        return sale_id

    except Exception as e:
        connection.rollback()
        logger.error(f"Transaction failed during sale creation: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to save sale: {str(e)}")
    finally:
        cursor.close()
        connection.close()
