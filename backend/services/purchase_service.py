import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.purchase_service')


class ValidationError(Exception):
    """Custom exception for purchase business validation errors."""
    pass


def to_decimal(val, default=Decimal('0.00')):
    """Safely convert a value to Decimal with 2 decimal places."""
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"Invalid monetary or numeric amount: {val}")


def get_all_purchases(search=None, supplier_id=None, status=None, date_from=None, date_to=None):
    """
    Fetch all purchase records with supplier info, item counts, and total quantities.
    Supports filtering by search (invoice / supplier name), supplier_id, status, and date range.
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
            p.created_at,
            p.created_by,
            u.name AS created_by_name,
            s.supplier_id,
            s.supplier_name,
            s.phone AS supplier_phone,
            COUNT(pi.purchase_item_id) AS item_count,
            COALESCE(SUM(pi.quantity), 0) AS total_quantity
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        JOIN users u ON p.created_by = u.user_id
        LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        WHERE 1=1
    """
    params = []

    if supplier_id:
        sql += " AND p.supplier_id = %s"
        params.append(supplier_id)

    if status and status.upper() != 'ALL':
        sql += " AND p.payment_status = %s"
        params.append(status.upper())

    if date_from:
        sql += " AND p.purchase_date >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND p.purchase_date <= %s"
        params.append(date_to)

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (p.invoice_number LIKE %s OR s.supplier_name LIKE %s)"
        params.extend([search_term, search_term])

    sql += " GROUP BY p.purchase_id, s.supplier_id, u.user_id ORDER BY p.purchase_date DESC, p.purchase_id DESC"
    return query_db(sql, tuple(params))


def get_purchase_summary_metrics():
    """
    Calculate high-level purchase metrics from the live database.
    - Total Purchases (count)
    - This Month (count & value)
    - Total Purchase Value
    - Pending/Unpaid Purchase Amount
    """
    today = date.today()
    first_day_of_month = today.replace(day=1)

    # All-time metrics
    all_time_sql = """
        SELECT 
            COUNT(*) AS total_purchases,
            COALESCE(SUM(total), 0) AS total_purchase_value,
            COALESCE(SUM(CASE WHEN payment_status IN ('PENDING', 'PARTIAL') THEN total ELSE 0 END), 0) AS pending_purchase_value
        FROM purchases
    """
    all_time = query_db(all_time_sql, one=True) or {}

    # This month metrics
    month_sql = """
        SELECT 
            COUNT(*) AS this_month_count,
            COALESCE(SUM(total), 0) AS this_month_value
        FROM purchases
        WHERE purchase_date >= %s AND purchase_date <= %s
    """
    month_data = query_db(month_sql, (first_day_of_month, today), one=True) or {}

    return {
        'total_purchases': all_time.get('total_purchases', 0) or 0,
        'total_purchase_value': all_time.get('total_purchase_value', Decimal('0.00')) or Decimal('0.00'),
        'pending_purchase_value': all_time.get('pending_purchase_value', Decimal('0.00')) or Decimal('0.00'),
        'this_month_count': month_data.get('this_month_count', 0) or 0,
        'this_month_value': month_data.get('this_month_value', Decimal('0.00')) or Decimal('0.00')
    }


def get_purchase_by_id(purchase_id):
    """
    Fetch a single purchase by ID with supplier and user details.
    """
    sql = """
        SELECT 
            p.purchase_id,
            p.supplier_id,
            s.supplier_name,
            s.contact_person,
            s.phone AS supplier_phone,
            s.email AS supplier_email,
            s.address AS supplier_address,
            s.gst_number AS supplier_gst,
            s.status AS supplier_status,
            p.invoice_number,
            p.purchase_date,
            p.subtotal,
            p.discount,
            p.tax,
            p.total,
            p.payment_status,
            p.notes,
            p.created_by,
            u.name AS created_by_name,
            p.created_at,
            p.updated_at,
            COUNT(pi.purchase_item_id) AS item_count,
            COALESCE(SUM(pi.quantity), 0) AS total_quantity
        FROM purchases p
        JOIN suppliers s ON p.supplier_id = s.supplier_id
        JOIN users u ON p.created_by = u.user_id
        LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        WHERE p.purchase_id = %s
        GROUP BY p.purchase_id, s.supplier_id, u.user_id
    """
    return query_db(sql, (purchase_id,), one=True)


def get_purchase_items(purchase_id):
    """
    Fetch all line items belonging to a purchase with complete variant details.
    """
    sql = """
        SELECT 
            pi.purchase_item_id,
            pi.purchase_id,
            pi.variant_id,
            pi.quantity,
            pi.unit_price,
            pi.total_price,
            pi.created_at,
            pv.sku,
            pv.size,
            pv.color,
            pv.selling_price,
            pv.stock_quantity AS current_stock,
            p.product_id,
            p.product_name,
            p.brand,
            p.material,
            c.category_name
        FROM purchase_items pi
        JOIN product_variants pv ON pi.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE pi.purchase_id = %s
        ORDER BY pi.purchase_item_id ASC
    """
    return query_db(sql, (purchase_id,))


def get_active_suppliers():
    """
    Fetch list of active suppliers for the purchase creation dropdown.
    """
    sql = """
        SELECT supplier_id, supplier_name, contact_person, phone, email, gst_number
        FROM suppliers
        WHERE status = 'ACTIVE'
        ORDER BY supplier_name ASC
    """
    return query_db(sql)


def get_active_variants():
    """
    Fetch all active product variants belonging to active products.
    Includes product name, category, SKU, size, color, current stock, and purchase price.
    """
    sql = """
        SELECT 
            pv.variant_id,
            pv.product_id,
            p.product_name,
            p.brand,
            c.category_name,
            pv.sku,
            pv.size,
            pv.color,
            pv.purchase_price,
            pv.selling_price,
            pv.stock_quantity
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE pv.status = 'ACTIVE' AND p.status = 'ACTIVE'
        ORDER BY p.product_name ASC, pv.sku ASC
    """
    return query_db(sql)


def validate_purchase_data(purchase_data, items_data):
    """
    Validate all header fields and line items before starting the database transaction.
    Returns sanitized and calculated values:
    (supplier_id, invoice_number, purchase_date, payment_status, discount, tax, notes, validated_items, subtotal, grand_total)
    """
    # 1. Supplier Validation
    supplier_id = purchase_data.get('supplier_id')
    if not supplier_id:
        raise ValidationError("Supplier is required.")
    try:
        supplier_id = int(supplier_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid supplier ID.")

    supplier = query_db("SELECT supplier_id, supplier_name, status FROM suppliers WHERE supplier_id = %s", (supplier_id,), one=True)
    if not supplier:
        raise ValidationError("Selected supplier does not exist.")
    if supplier['status'] != 'ACTIVE':
        raise ValidationError(f"Supplier '{supplier['supplier_name']}' is inactive. Purchases can only be recorded for active suppliers.")

    # 2. Invoice Number Validation
    invoice_number = (purchase_data.get('invoice_number') or '').strip()
    if not invoice_number:
        raise ValidationError("Purchase invoice / reference number is required.")
    if len(invoice_number) > 50:
        raise ValidationError("Invoice number cannot exceed 50 characters.")

    # 3. Purchase Date Validation
    purchase_date_raw = purchase_data.get('purchase_date')
    if not purchase_date_raw:
        raise ValidationError("Purchase date is required.")
    if isinstance(purchase_date_raw, str):
        try:
            purchase_date = datetime.strptime(purchase_date_raw.strip(), '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError("Invalid purchase date format. Use YYYY-MM-DD.")
    elif isinstance(purchase_date_raw, (date, datetime)):
        purchase_date = purchase_date_raw if isinstance(purchase_date_raw, date) else purchase_date_raw.date()
    else:
        raise ValidationError("Invalid purchase date.")

    # 4. Payment Status Validation
    payment_status = (purchase_data.get('payment_status') or 'PAID').strip().upper()
    if payment_status not in ('PAID', 'PARTIAL', 'PENDING'):
        raise ValidationError(f"Invalid payment status '{payment_status}'. Allowed values: PAID, PARTIAL, PENDING.")

    # 5. Discount and Tax Validation
    try:
        discount = to_decimal(purchase_data.get('discount', '0.00'))
    except ValidationError:
        raise ValidationError("Discount must be a valid non-negative number.")
    if discount < Decimal('0.00'):
        raise ValidationError("Discount cannot be negative.")

    try:
        tax = to_decimal(purchase_data.get('tax', '0.00'))
    except ValidationError:
        raise ValidationError("Tax must be a valid non-negative number.")
    if tax < Decimal('0.00'):
        raise ValidationError("Tax cannot be negative.")

    notes = (purchase_data.get('notes') or '').strip() or None

    # 6. Items Validation
    if not items_data or len(items_data) == 0:
        raise ValidationError("A purchase must contain at least one product variant item.")

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
            raise ValidationError(f"Duplicate variant detected (Variant ID {variant_id}). Each variant can only appear once per purchase. Please combine quantities into a single row.")
        seen_variants.add(variant_id)

        # Check variant exists and is active, product is active
        variant = query_db("""
            SELECT 
                pv.variant_id, 
                pv.sku, 
                pv.size, 
                pv.color, 
                pv.status AS variant_status, 
                pv.stock_quantity,
                p.product_name, 
                p.status AS product_status
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.product_id
            WHERE pv.variant_id = %s
        """, (variant_id,), one=True)

        if not variant:
            raise ValidationError(f"Row {idx}: Variant ID {variant_id} does not exist.")
        if variant['product_status'] != 'ACTIVE':
            raise ValidationError(f"Row {idx}: Product '{variant['product_name']}' is inactive and cannot be purchased.")
        if variant['variant_status'] != 'ACTIVE':
            raise ValidationError(f"Row {idx}: Variant SKU '{variant['sku']}' ({variant['product_name']}) is inactive and cannot be purchased.")

        # Quantity validation (> 0)
        quantity_raw = item.get('quantity')
        try:
            quantity = int(quantity_raw)
        except (ValueError, TypeError):
            raise ValidationError(f"Row {idx} ({variant['sku']}): Quantity must be a valid integer.")
        if quantity <= 0:
            raise ValidationError(f"Row {idx} ({variant['sku']}): Quantity must be greater than zero. Received: {quantity}.")

        # Unit Price validation (>= 0)
        unit_price_raw = item.get('unit_price')
        try:
            unit_price = to_decimal(unit_price_raw)
        except ValidationError:
            raise ValidationError(f"Row {idx} ({variant['sku']}): Unit price must be a valid number.")
        if unit_price < Decimal('0.00'):
            raise ValidationError(f"Row {idx} ({variant['sku']}): Unit price cannot be negative. Received: ₹{unit_price}.")

        line_total = (Decimal(quantity) * unit_price).quantize(Decimal('0.01'))
        subtotal += line_total

        validated_items.append({
            'variant_id': variant_id,
            'sku': variant['sku'],
            'product_name': variant['product_name'],
            'quantity': quantity,
            'unit_price': unit_price.quantize(Decimal('0.01')),
            'total_price': line_total
        })

    # Subtotal, Discount, Tax and Grand Total calculations
    grand_total = (subtotal - discount + tax).quantize(Decimal('0.01'))
    if grand_total < Decimal('0.00'):
        raise ValidationError(f"Calculated grand total (₹{grand_total}) cannot be negative. Discount (₹{discount}) exceeds subtotal + tax (₹{subtotal + tax}).")

    return (
        supplier_id,
        invoice_number,
        purchase_date,
        payment_status,
        discount.quantize(Decimal('0.01')),
        tax.quantize(Decimal('0.01')),
        notes,
        validated_items,
        subtotal.quantize(Decimal('0.01')),
        grand_total
    )


def create_purchase(purchase_data, items_data, user_id):
    """
    Atomically creates a purchase record with line items, increments stock,
    and creates audit stock movements.
    
    If ANY step fails, rolls back the entire transaction.
    """
    # Pre-validate all data
    (
        supplier_id,
        invoice_number,
        purchase_date,
        payment_status,
        discount,
        tax,
        notes,
        validated_items,
        subtotal,
        grand_total
    ) = validate_purchase_data(purchase_data, items_data)

    if not user_id:
        raise ValidationError("User ID is required to create a purchase record.")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Insert Purchase Header
        insert_purchase_sql = """
            INSERT INTO purchases (
                supplier_id, 
                invoice_number, 
                purchase_date, 
                subtotal, 
                discount, 
                tax, 
                total, 
                payment_status, 
                notes, 
                created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_purchase_sql, (
            supplier_id,
            invoice_number,
            purchase_date,
            subtotal,
            discount,
            tax,
            grand_total,
            payment_status,
            notes,
            user_id
        ))
        purchase_id = cursor.lastrowid

        # 2. Process Line Items
        insert_item_sql = """
            INSERT INTO purchase_items (
                purchase_id,
                variant_id,
                quantity,
                unit_price,
                total_price
            ) VALUES (%s, %s, %s, %s, %s)
        """

        update_stock_sql = """
            UPDATE product_variants
            SET stock_quantity = stock_quantity + %s
            WHERE variant_id = %s
        """

        insert_movement_sql = """
            INSERT INTO stock_movements (
                variant_id,
                movement_type,
                quantity,
                reference_type,
                reference_id,
                notes,
                created_by
            ) VALUES (%s, 'PURCHASE', %s, 'PURCHASE', %s, %s, %s)
        """

        for item in validated_items:
            # 2a. Insert Purchase Item
            cursor.execute(insert_item_sql, (
                purchase_id,
                item['variant_id'],
                item['quantity'],
                item['unit_price'],
                item['total_price']
            ))

            # 2b. Increment Variant Stock
            cursor.execute(update_stock_sql, (
                item['quantity'],
                item['variant_id']
            ))
            if cursor.rowcount == 0:
                raise Exception(f"Failed to update stock for variant ID {item['variant_id']}")

            # 2c. Insert Stock Movement Audit
            movement_notes = f"Inward stock via Purchase #{invoice_number} ({item['quantity']} units)"
            cursor.execute(insert_movement_sql, (
                item['variant_id'],
                item['quantity'],
                purchase_id,
                movement_notes,
                user_id
            ))

        # Commit everything atomically
        connection.commit()
        logger.info(f"Purchase #{purchase_id} (Invoice: {invoice_number}) created successfully with {len(validated_items)} items.")
        return purchase_id

    except Exception as e:
        connection.rollback()
        logger.error(f"Transaction failed during purchase creation: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to save purchase: {str(e)}")
    finally:
        cursor.close()
        connection.close()
