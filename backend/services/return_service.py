"""
VL Silks – Returns & Exchanges Service
Handles atomic processing of garment returns, condition inspections (Restockable vs Damaged),
stock movement reversals, cash/credit refunds, and garment exchange workflows.
"""

import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.return_service')

ALLOWED_REFUND_TYPES = ('CASH', 'CREDIT_ADJUSTMENT', 'EXCHANGE')
ALLOWED_CONDITIONS = ('RESTOCKABLE', 'DAMAGED')


class ValidationError(Exception):
    """Custom exception for return/exchange validation errors."""
    pass


def to_decimal(val, default=Decimal('0.00')):
    """Safely convert a value to Decimal with 2 decimal places."""
    if val is None or val == '':
        return default
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(f"Invalid monetary or numeric amount: {val}")


def generate_return_reference(return_id):
    """Format return reference number string."""
    if not return_id:
        return "RET-UNKNOWN"
    return f"RET-2026-{int(return_id):04d}"


# ---------------------------------------------------------------------------
# 1. READ — Queries, Summaries, and Returnable Item Calculations
# ---------------------------------------------------------------------------

def get_all_returns(search=None, refund_type=None, date_from=None, date_to=None):
    """
    Fetch all returns with customer info, invoice details, item counts, and totals.
    Supports filtering by search term (return ID, invoice, customer name/phone),
    refund_type, and date range.
    """
    sql = """
        SELECT
            r.return_id,
            r.sale_id,
            s.invoice_number,
            s.sale_date,
            r.customer_id,
            c.customer_name,
            c.phone AS customer_phone,
            r.return_date,
            r.return_reason,
            r.total_refund_amount,
            r.refund_type,
            r.created_by,
            u.name AS created_by_name,
            r.created_at,
            COUNT(ri.return_item_id) AS item_count,
            COALESCE(SUM(ri.quantity), 0) AS total_quantity
        FROM returns r
        JOIN sales s ON r.sale_id = s.sale_id
        JOIN users u ON r.created_by = u.user_id
        LEFT JOIN customers c ON r.customer_id = c.customer_id
        LEFT JOIN return_items ri ON r.return_id = ri.return_id
        WHERE 1=1
    """
    params = []

    if refund_type and refund_type.upper() != 'ALL':
        sql += " AND r.refund_type = %s"
        params.append(refund_type.upper())

    if date_from:
        sql += " AND r.return_date >= %s"
        params.append(date_from)

    if date_to:
        sql += " AND r.return_date <= %s"
        params.append(date_to)

    if search:
        search_term = f"%{search.strip()}%"
        sql += " AND (s.invoice_number LIKE %s OR c.customer_name LIKE %s OR c.phone LIKE %s OR r.return_reason LIKE %s)"
        params.extend([search_term, search_term, search_term, search_term])

    sql += """
        GROUP BY r.return_id, s.sale_id, u.user_id, c.customer_id
        ORDER BY r.return_date DESC, r.return_id DESC
    """
    rows = query_db(sql, tuple(params)) or []
    for row in rows:
        row['return_reference'] = generate_return_reference(row['return_id'])
    return rows


def get_return_summary_metrics():
    """
    Calculate high-level Return & Exchange metrics.
    """
    today = date.today().strftime('%Y-%m-%d')
    sql = """
        SELECT
            COUNT(r.return_id) AS total_returns_count,
            COALESCE(SUM(r.total_refund_amount), 0.00) AS total_refunds_amount,
            COUNT(CASE WHEN r.return_date = %s THEN 1 END) AS today_returns_count,
            COALESCE(SUM(CASE WHEN r.return_date = %s THEN r.total_refund_amount ELSE 0 END), 0.00) AS today_refunds_amount,
            COUNT(CASE WHEN r.refund_type = 'EXCHANGE' THEN 1 END) AS total_exchanges_count,
            COUNT(CASE WHEN r.refund_type = 'CREDIT_ADJUSTMENT' THEN 1 END) AS total_credit_adjustments_count
        FROM returns r
    """
    row = query_db(sql, (today, today), one=True) or {}
    return {
        'total_returns_count': row.get('total_returns_count', 0) or 0,
        'total_refunds_amount': to_decimal(row.get('total_refunds_amount', Decimal('0.00'))),
        'today_returns_count': row.get('today_returns_count', 0) or 0,
        'today_refunds_amount': to_decimal(row.get('today_refunds_amount', Decimal('0.00'))),
        'total_exchanges_count': row.get('total_exchanges_count', 0) or 0,
        'total_credit_adjustments_count': row.get('total_credit_adjustments_count', 0) or 0,
    }


def get_return_by_id(return_id):
    """
    Fetch complete return details and all returned items.
    """
    if not return_id:
        return None

    sql = """
        SELECT
            r.return_id,
            r.sale_id,
            s.invoice_number,
            s.sale_date,
            s.total_amount AS original_sale_total,
            s.payment_method AS original_payment_method,
            r.customer_id,
            c.customer_name,
            c.phone AS customer_phone,
            c.email AS customer_email,
            c.address AS customer_address,
            r.return_date,
            r.return_reason,
            r.total_refund_amount,
            r.refund_type,
            r.created_by,
            u.name AS created_by_name,
            r.created_at
        FROM returns r
        JOIN sales s ON r.sale_id = s.sale_id
        JOIN users u ON r.created_by = u.user_id
        LEFT JOIN customers c ON r.customer_id = c.customer_id
        WHERE r.return_id = %s
    """
    ret = query_db(sql, (return_id,), one=True)
    if not ret:
        return None

    ret['return_reference'] = generate_return_reference(ret['return_id'])

    # Fetch return items with product variant details
    items_sql = """
        SELECT
            ri.return_item_id,
            ri.return_id,
            ri.sale_item_id,
            ri.variant_id,
            ri.quantity,
            ri.unit_price,
            ri.refund_amount,
            ri.condition_status,
            ri.created_at,
            pv.sku,
            pv.size,
            pv.color,
            pv.stock_quantity AS current_stock,
            p.product_name,
            p.brand,
            p.material,
            cat.category_name
        FROM return_items ri
        JOIN product_variants pv ON ri.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE ri.return_id = %s
        ORDER BY ri.return_item_id ASC
    """
    ret['items'] = query_db(items_sql, (return_id,)) or []
    return ret


def search_sales_for_returns(q, limit=20):
    """
    Search sales eligible for return processing.

    Matches against:
    - Sale ID (numeric prefix match)
    - Invoice number (partial)
    - Customer name (partial)
    - Customer phone (partial)
    - Product SKU in that sale (partial)

    Returns only sales that are NOT fully returned (have at least one item
    with remaining returnable quantity).

    Excludes VOID sales.
    """
    if not q or not q.strip():
        return []

    q = q.strip()
    params = []

    # Build LIKE term for text fields
    like = f"%{q}%"

    # Numeric prefix check for sale_id / invoice search
    sale_id_clause = ""
    if q.isdigit():
        sale_id_clause = "OR s.sale_id = %s"
        params_numeric = [int(q)]
    else:
        params_numeric = []

    sql = """
        SELECT DISTINCT
            s.sale_id,
            s.invoice_number,
            s.sale_date,
            s.total_amount,
            s.payment_method,
            s.payment_status,
            c.customer_id,
            c.customer_name,
            c.phone AS customer_phone,
            (
                SELECT COUNT(*)
                FROM sale_items si2
                WHERE si2.sale_id = s.sale_id
                  AND (
                    si2.quantity - COALESCE((
                        SELECT SUM(ri2.quantity)
                        FROM return_items ri2
                        WHERE ri2.sale_item_id = si2.sale_item_id
                    ), 0)
                  ) > 0
            ) AS returnable_items_count,
            (
                SELECT COUNT(*)
                FROM returns r2
                WHERE r2.sale_id = s.sale_id
            ) AS existing_returns_count
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        LEFT JOIN product_variants pv ON si.variant_id = pv.variant_id
        WHERE s.payment_status != 'VOID'
          AND (
              s.invoice_number LIKE %s
              OR c.customer_name LIKE %s
              OR c.phone LIKE %s
              OR pv.sku LIKE %s
              {sale_id_extra}
          )
        ORDER BY s.sale_id DESC
        LIMIT %s
    """.format(sale_id_extra=sale_id_clause if q.isdigit() else "")

    # Build params list in the right order
    base_params = [like, like, like, like]
    if q.isdigit():
        base_params.extend(params_numeric)
    base_params.append(limit)

    rows = query_db(sql, tuple(base_params)) or []

    result = []
    for row in rows:
        result.append({
            'sale_id': row['sale_id'],
            'invoice_number': row['invoice_number'],
            'sale_date': str(row['sale_date']),
            'total_amount': float(row['total_amount']),
            'payment_method': row['payment_method'],
            'payment_status': row['payment_status'],
            'customer_id': row['customer_id'],
            'customer_name': row['customer_name'] or 'Walk-in Customer',
            'customer_phone': row['customer_phone'] or '',
            'returnable_items_count': int(row['returnable_items_count'] or 0),
            'existing_returns_count': int(row['existing_returns_count'] or 0),
            'is_fully_returned': int(row['returnable_items_count'] or 0) == 0,
        })
    return result


def get_sale_returnable_items(sale_id):
    """
    Calculate returnable quantity and effective refund rate for each line item of a sale.
    Accounts for all historical returns on this sale.
    """
    if not sale_id:
        return None, []

    sale_sql = """
        SELECT
            s.sale_id,
            s.invoice_number,
            s.sale_date,
            s.total_amount,
            s.paid_amount,
            s.balance_amount,
            s.payment_method,
            s.payment_status,
            s.customer_id,
            c.customer_name,
            c.phone AS customer_phone
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        WHERE s.sale_id = %s
    """
    sale = query_db(sale_sql, (sale_id,), one=True)
    if not sale:
        return None, []

    items_sql = """
        SELECT
            si.sale_item_id,
            si.sale_id,
            si.variant_id,
            si.quantity AS sold_quantity,
            si.unit_price,
            si.discount,
            si.total_price,
            pv.sku,
            pv.size,
            pv.color,
            pv.stock_quantity AS current_stock,
            pv.status AS variant_status,
            p.product_name,
            p.brand,
            cat.category_name,
            COALESCE((
                SELECT SUM(ri.quantity)
                FROM return_items ri
                WHERE ri.sale_item_id = si.sale_item_id
            ), 0) AS already_returned_quantity
        FROM sale_items si
        JOIN product_variants pv ON si.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories cat ON p.category_id = cat.category_id
        WHERE si.sale_id = %s
        ORDER BY si.sale_item_id ASC
    """
    items = query_db(items_sql, (sale_id,)) or []
    returnable_items = []

    for item in items:
        item_dict = dict(item)
        sold_qty = item_dict['sold_quantity']
        returned_qty = item_dict['already_returned_quantity']
        returnable_qty = max(0, sold_qty - returned_qty)
        
        # Effective unit price considering discounts
        if sold_qty > 0:
            effective_unit_price = (to_decimal(item_dict['total_price']) / Decimal(str(sold_qty))).quantize(Decimal('0.01'))
        else:
            effective_unit_price = to_decimal(item_dict['unit_price'])

        item_dict['returnable_quantity'] = returnable_qty
        item_dict['effective_unit_price'] = effective_unit_price
        item_dict['is_returnable'] = returnable_qty > 0
        returnable_items.append(item_dict)

    return sale, returnable_items


# ---------------------------------------------------------------------------
# 2. WRITE — Atomic Return Processing
# ---------------------------------------------------------------------------

def create_return(return_data, items_data, user_id):
    """
    Process a customer return in a single atomic database transaction.
    
    Workflow:
      1. Lock and validate sale.
      2. Lock and validate returnable quantities for each item.
      3. Insert `returns` master record.
      4. Insert `return_items` line records.
      5. If condition == RESTOCKABLE:
           - Increment `product_variants.stock_quantity`
           - Insert `stock_movements` (CUSTOMER_RETURN)
      6. If condition == DAMAGED:
           - Do not increment sellable stock
      7. If refund_type == CREDIT_ADJUSTMENT:
           - Insert `credit_transactions` (RETURN_REFUND) to reduce customer Udhaar
      8. Commit transaction.
    """
    if not return_data or not isinstance(return_data, dict):
        raise ValidationError("Return data dictionary is required.")
    if not items_data or not isinstance(items_data, list):
        raise ValidationError("At least one return item must be specified.")
    if not user_id:
        raise ValidationError("Authenticated user ID is required.")

    sale_id = return_data.get('sale_id')
    if not sale_id:
        raise ValidationError("Original sale_id is required.")

    refund_type = (return_data.get('refund_type') or 'CASH').upper().strip()
    if refund_type not in ALLOWED_REFUND_TYPES:
        raise ValidationError(f"Invalid refund_type: '{refund_type}'. Must be one of {ALLOWED_REFUND_TYPES}.")

    return_date_val = return_data.get('return_date') or date.today().strftime('%Y-%m-%d')
    if isinstance(return_date_val, (date, datetime)):
        return_date_str = return_date_val.strftime('%Y-%m-%d')
    else:
        return_date_str = str(return_date_val).strip()
        try:
            datetime.strptime(return_date_str, '%Y-%m-%d')
        except ValueError:
            raise ValidationError(f"Invalid return_date format: '{return_date_val}'. Expected YYYY-MM-DD.")

    return_reason = (return_data.get('return_reason') or '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Lock original sale
        cursor.execute("SELECT * FROM sales WHERE sale_id = %s FOR UPDATE", (sale_id,))
        sale = cursor.fetchone()
        if not sale:
            raise ValidationError(f"Original sale #{sale_id} was not found.")

        customer_id = sale.get('customer_id') or return_data.get('customer_id')

        if refund_type == 'CREDIT_ADJUSTMENT' and not customer_id:
            raise ValidationError("Credit adjustment refund requires an invoice linked to a registered customer.")

        # 2. Lock and validate items
        validated_items = []
        total_calculated_refund = Decimal('0.00')

        # Filter out items with quantity <= 0 if form submitted empty fields
        active_items = []
        for raw_item in items_data:
            qty_raw = raw_item.get('quantity')
            try:
                qty_int = int(qty_raw)
                if qty_int > 0:
                    active_items.append((raw_item, qty_int))
            except (ValueError, TypeError):
                continue

        if not active_items:
            raise ValidationError("At least one item with a valid positive return quantity must be selected.")

        for raw_item, qty_int in active_items:
            sale_item_id = raw_item.get('sale_item_id')
            variant_id = raw_item.get('variant_id')

            # Fetch sale_item
            if sale_item_id:
                cursor.execute("""
                    SELECT si.*, pv.sku, pv.stock_quantity as current_stock 
                    FROM sale_items si 
                    JOIN product_variants pv ON si.variant_id = pv.variant_id 
                    WHERE si.sale_item_id = %s AND si.sale_id = %s 
                    FOR UPDATE
                """, (sale_item_id, sale_id))
            elif variant_id:
                cursor.execute("""
                    SELECT si.*, pv.sku, pv.stock_quantity as current_stock 
                    FROM sale_items si 
                    JOIN product_variants pv ON si.variant_id = pv.variant_id 
                    WHERE si.variant_id = %s AND si.sale_id = %s 
                    FOR UPDATE
                """, (variant_id, sale_id))
            else:
                raise ValidationError("Each return item must specify sale_item_id or variant_id.")

            sale_item = cursor.fetchone()
            if not sale_item:
                raise ValidationError(f"Item not found on sale #{sale_id}.")

            actual_sale_item_id = sale_item['sale_item_id']
            actual_variant_id = sale_item['variant_id']
            sku = sale_item['sku']
            sold_qty = sale_item['quantity']

            # Calculate already returned quantity with FOR UPDATE locking
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0) AS returned_qty
                FROM return_items
                WHERE sale_item_id = %s
            """, (actual_sale_item_id,))
            ret_row = cursor.fetchone()
            already_returned = ret_row['returned_qty'] if ret_row else 0

            returnable_qty = sold_qty - already_returned
            if qty_int > returnable_qty:
                raise ValidationError(
                    f"Cannot return {qty_int} unit(s) of '{sku}'. "
                    f"Sold: {sold_qty}, Already returned: {already_returned}, Remaining returnable: {returnable_qty}."
                )

            # Condition Check
            condition = (raw_item.get('condition_status') or 'RESTOCKABLE').upper().strip()
            if condition not in ALLOWED_CONDITIONS:
                raise ValidationError(f"Invalid condition_status '{condition}' for '{sku}'. Must be RESTOCKABLE or DAMAGED.")

            # Calculate line refund amount based on original net selling price
            unit_price = to_decimal(sale_item['unit_price'])
            item_total = to_decimal(sale_item['total_price'])
            effective_unit_price = (item_total / Decimal(str(sold_qty))).quantize(Decimal('0.01'))
            line_refund = (effective_unit_price * Decimal(str(qty_int))).quantize(Decimal('0.01'))

            total_calculated_refund += line_refund

            validated_items.append({
                'sale_item_id': actual_sale_item_id,
                'variant_id': actual_variant_id,
                'sku': sku,
                'quantity': qty_int,
                'unit_price': unit_price,
                'effective_unit_price': effective_unit_price,
                'refund_amount': line_refund,
                'condition_status': condition,
            })

        # 3. Insert `returns` record
        cursor.execute("""
            INSERT INTO returns 
            (sale_id, customer_id, return_date, return_reason, total_refund_amount, refund_type, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            sale_id,
            customer_id,
            return_date_str,
            return_reason or 'Customer garment return',
            total_calculated_refund,
            refund_type,
            user_id
        ))
        return_id = cursor.lastrowid
        return_ref = generate_return_reference(return_id)

        # 4. Insert `return_items` and process stock movements
        for item in validated_items:
            cursor.execute("""
                INSERT INTO return_items
                (return_id, sale_item_id, variant_id, quantity, unit_price, refund_amount, condition_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                return_id,
                item['sale_item_id'],
                item['variant_id'],
                item['quantity'],
                item['unit_price'],
                item['refund_amount'],
                item['condition_status']
            ))

            # Stock update & stock movement
            if item['condition_status'] == 'RESTOCKABLE':
                cursor.execute("""
                    UPDATE product_variants
                    SET stock_quantity = stock_quantity + %s
                    WHERE variant_id = %s
                """, (item['quantity'], item['variant_id']))

                cursor.execute("""
                    INSERT INTO stock_movements
                    (variant_id, movement_type, quantity, reference_type, reference_id, notes, created_by)
                    VALUES (%s, 'CUSTOMER_RETURN', %s, 'RETURN', %s, %s, %s)
                """, (
                    item['variant_id'],
                    item['quantity'],
                    return_id,
                    f"Customer return #{return_id} ({return_ref}) for invoice {sale['invoice_number']} - restocked in sellable inventory",
                    user_id
                ))
            else:
                # DAMAGED condition: do not increase sellable inventory, record audit trail
                cursor.execute("""
                    INSERT INTO stock_movements
                    (variant_id, movement_type, quantity, reference_type, reference_id, notes, created_by)
                    VALUES (%s, 'DAMAGE', 0, 'RETURN', %s, %s, %s)
                """, (
                    item['variant_id'],
                    return_id,
                    f"Customer return #{return_id} ({return_ref}) marked DAMAGED - item written off / not returned to active stock",
                    user_id
                ))

        # 5. Financial / Refund Settlement
        if refund_type == 'CREDIT_ADJUSTMENT':
            cursor.execute("""
                INSERT INTO credit_transactions
                (customer_id, sale_id, payment_id, transaction_type, amount, transaction_date, notes, created_by)
                VALUES (%s, %s, NULL, 'RETURN_REFUND', %s, %s, %s, %s)
            """, (
                customer_id,
                sale_id,
                total_calculated_refund,
                return_date_str,
                f"Credit ledger adjustment for Return #{return_id} ({return_ref}) on invoice {sale['invoice_number']}",
                user_id
            ))

        conn.commit()
        logger.info(f"Return #{return_id} ({return_ref}) created successfully. Refund: ₹{total_calculated_refund} via {refund_type}.")

        return {
            'return_id': return_id,
            'return_reference': return_ref,
            'sale_id': sale_id,
            'invoice_number': sale['invoice_number'],
            'customer_id': customer_id,
            'return_date': return_date_str,
            'total_refund_amount': total_calculated_refund,
            'refund_type': refund_type,
            'item_count': len(validated_items),
            'items': validated_items
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed during return creation: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


# ---------------------------------------------------------------------------
# 3. WRITE — Atomic Garment Exchange Processing
# ---------------------------------------------------------------------------

def process_exchange(exchange_data, old_items_data, new_items_data, user_id):
    """
    Process a full garment exchange in a single atomic database transaction.
    
    Workflow:
      1. Lock old sale and validate returnable quantity for old item(s).
      2. Calculate old returned value.
      3. Lock new replacement variant(s) and verify active status & stock availability.
      4. Calculate new replacement items value.
      5. Calculate price difference: `price_diff = new_value - old_value`.
      6. Process return of old item (Restock if RESTOCKABLE).
      7. Deduct stock for new replacement item(s) and record SALE movement under reference RETURN.
      8. If price_diff > 0: Customer pays additional difference.
      9. If price_diff < 0: Customer receives refund / credit difference.
     10. Commit transaction.
    """
    if not exchange_data or not isinstance(exchange_data, dict):
        raise ValidationError("Exchange data dictionary is required.")
    if not old_items_data or not isinstance(old_items_data, list):
        raise ValidationError("Old returned item(s) must be specified for exchange.")
    if not new_items_data or not isinstance(new_items_data, list):
        raise ValidationError("New replacement item(s) must be specified for exchange.")
    if not user_id:
        raise ValidationError("Authenticated user ID is required.")

    sale_id = exchange_data.get('sale_id')
    if not sale_id:
        raise ValidationError("Original sale_id is required for exchange.")

    return_date_val = exchange_data.get('return_date') or date.today().strftime('%Y-%m-%d')
    if isinstance(return_date_val, (date, datetime)):
        return_date_str = return_date_val.strftime('%Y-%m-%d')
    else:
        return_date_str = str(return_date_val).strip()

    exchange_notes = (exchange_data.get('notes') or '').strip()
    diff_payment_method = (exchange_data.get('payment_method') or 'CASH').upper().strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Lock original sale
        cursor.execute("SELECT * FROM sales WHERE sale_id = %s FOR UPDATE", (sale_id,))
        sale = cursor.fetchone()
        if not sale:
            raise ValidationError(f"Original sale #{sale_id} was not found.")

        customer_id = sale.get('customer_id') or exchange_data.get('customer_id')

        # 2. Validate and calculate old returned items value
        validated_old_items = []
        old_total_value = Decimal('0.00')

        for raw_old in old_items_data:
            qty_int = int(raw_old.get('quantity', 0))
            if qty_int <= 0:
                continue

            sale_item_id = raw_old.get('sale_item_id')
            variant_id = raw_old.get('variant_id')

            if sale_item_id:
                cursor.execute("""
                    SELECT si.*, pv.sku 
                    FROM sale_items si 
                    JOIN product_variants pv ON si.variant_id = pv.variant_id 
                    WHERE si.sale_item_id = %s AND si.sale_id = %s 
                    FOR UPDATE
                """, (sale_item_id, sale_id))
            else:
                cursor.execute("""
                    SELECT si.*, pv.sku 
                    FROM sale_items si 
                    JOIN product_variants pv ON si.variant_id = pv.variant_id 
                    WHERE si.variant_id = %s AND si.sale_id = %s 
                    FOR UPDATE
                """, (variant_id, sale_id))

            sale_item = cursor.fetchone()
            if not sale_item:
                raise ValidationError(f"Item not found on sale #{sale_id}.")

            # Calculate remaining returnable
            cursor.execute("""
                SELECT COALESCE(SUM(quantity), 0) AS returned_qty
                FROM return_items
                WHERE sale_item_id = %s
            """, (sale_item['sale_item_id'],))
            ret_row = cursor.fetchone()
            already_ret = ret_row['returned_qty'] if ret_row else 0
            returnable_qty = sale_item['quantity'] - already_ret

            if qty_int > returnable_qty:
                raise ValidationError(
                    f"Cannot exchange {qty_int} unit(s) of '{sale_item['sku']}'. "
                    f"Only {returnable_qty} returnable."
                )

            condition = (raw_old.get('condition_status') or 'RESTOCKABLE').upper().strip()
            if condition not in ALLOWED_CONDITIONS:
                raise ValidationError(f"Invalid condition_status '{condition}'. Must be RESTOCKABLE or DAMAGED.")

            sold_qty = sale_item['quantity']
            item_total = to_decimal(sale_item['total_price'])
            effective_unit_price = (item_total / Decimal(str(sold_qty))).quantize(Decimal('0.01'))
            line_val = (effective_unit_price * Decimal(str(qty_int))).quantize(Decimal('0.01'))

            old_total_value += line_val
            validated_old_items.append({
                'sale_item_id': sale_item['sale_item_id'],
                'variant_id': sale_item['variant_id'],
                'sku': sale_item['sku'],
                'quantity': qty_int,
                'unit_price': to_decimal(sale_item['unit_price']),
                'effective_unit_price': effective_unit_price,
                'refund_amount': line_val,
                'condition_status': condition,
            })

        if not validated_old_items:
            raise ValidationError("At least one old item must be returned for the exchange.")

        # 3. Validate replacement items and stock availability
        validated_new_items = []
        new_total_value = Decimal('0.00')

        for raw_new in new_items_data:
            new_qty = int(raw_new.get('quantity', 0))
            if new_qty <= 0:
                continue

            new_var_id = raw_new.get('variant_id')
            if not new_var_id:
                raise ValidationError("Replacement variant ID is required.")

            cursor.execute("""
                SELECT pv.*, p.product_name, p.status as product_status 
                FROM product_variants pv 
                JOIN products p ON pv.product_id = p.product_id 
                WHERE pv.variant_id = %s 
                FOR UPDATE
            """, (new_var_id,))
            new_var = cursor.fetchone()
            if not new_var:
                raise ValidationError(f"Replacement variant #{new_var_id} does not exist.")

            if new_var['status'] != 'ACTIVE' or new_var['product_status'] != 'ACTIVE':
                raise ValidationError(f"Replacement variant '{new_var['sku']}' is inactive.")

            if new_var['stock_quantity'] < new_qty:
                raise ValidationError(
                    f"Insufficient stock for replacement variant '{new_var['sku']}'. "
                    f"Available stock: {new_var['stock_quantity']}, requested: {new_qty}."
                )

            new_selling_price = to_decimal(new_var['selling_price'])
            line_new_val = (new_selling_price * Decimal(str(new_qty))).quantize(Decimal('0.01'))
            new_total_value += line_new_val

            validated_new_items.append({
                'variant_id': new_var['variant_id'],
                'sku': new_var['sku'],
                'product_name': new_var['product_name'],
                'quantity': new_qty,
                'selling_price': new_selling_price,
                'total_value': line_new_val
            })

        if not validated_new_items:
            raise ValidationError("At least one replacement variant must be selected for exchange.")

        # 4. Calculate Price Difference
        price_difference = new_total_value - old_total_value  # Positive: Customer owes; Negative: Store owes

        # 5. Insert `returns` record with refund_type = 'EXCHANGE'
        reason_text = f"Exchange: Returned {len(validated_old_items)} item(s) for {len(validated_new_items)} replacement item(s). {exchange_notes}".strip()
        cursor.execute("""
            INSERT INTO returns 
            (sale_id, customer_id, return_date, return_reason, total_refund_amount, refund_type, created_by)
            VALUES (%s, %s, %s, %s, %s, 'EXCHANGE', %s)
        """, (
            sale_id,
            customer_id,
            return_date_str,
            reason_text,
            old_total_value,
            user_id
        ))
        return_id = cursor.lastrowid
        return_ref = generate_return_reference(return_id)

        # 6. Insert `return_items` and process old items stock
        for item in validated_old_items:
            cursor.execute("""
                INSERT INTO return_items
                (return_id, sale_item_id, variant_id, quantity, unit_price, refund_amount, condition_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                return_id,
                item['sale_item_id'],
                item['variant_id'],
                item['quantity'],
                item['unit_price'],
                item['refund_amount'],
                item['condition_status']
            ))

            if item['condition_status'] == 'RESTOCKABLE':
                cursor.execute("""
                    UPDATE product_variants
                    SET stock_quantity = stock_quantity + %s
                    WHERE variant_id = %s
                """, (item['quantity'], item['variant_id']))

                cursor.execute("""
                    INSERT INTO stock_movements
                    (variant_id, movement_type, quantity, reference_type, reference_id, notes, created_by)
                    VALUES (%s, 'CUSTOMER_RETURN', %s, 'RETURN', %s, %s, %s)
                """, (
                    item['variant_id'],
                    item['quantity'],
                    return_id,
                    f"Exchange #{return_id} ({return_ref}) old item returned & restocked",
                    user_id
                ))

        # 7. Deduct stock for new replacement items and create stock movements
        for item in validated_new_items:
            cursor.execute("""
                UPDATE product_variants
                SET stock_quantity = stock_quantity - %s
                WHERE variant_id = %s
            """, (item['quantity'], item['variant_id']))

            cursor.execute("""
                INSERT INTO stock_movements
                (variant_id, movement_type, quantity, reference_type, reference_id, notes, created_by)
                VALUES (%s, 'SALE', %s, 'RETURN', %s, %s, %s)
            """, (
                item['variant_id'],
                -item['quantity'],
                return_id,
                f"Exchange #{return_id} ({return_ref}) issued replacement {item['sku']}",
                user_id
            ))

        # 8. Financial adjustments based on price difference
        if price_difference < Decimal('0.00') and diff_payment_method == 'CREDIT_ADJUSTMENT' and customer_id:
            # Customer receives credit refund for the difference
            cursor.execute("""
                INSERT INTO credit_transactions
                (customer_id, sale_id, payment_id, transaction_type, amount, transaction_date, notes, created_by)
                VALUES (%s, %s, NULL, 'RETURN_REFUND', %s, %s, %s, %s)
            """, (
                customer_id,
                sale_id,
                abs(price_difference),
                return_date_str,
                f"Exchange #{return_id} balance refund credit difference",
                user_id
            ))

        conn.commit()
        logger.info(f"Exchange #{return_id} ({return_ref}) processed successfully. Price difference: ₹{price_difference}")

        return {
            'return_id': return_id,
            'return_reference': return_ref,
            'sale_id': sale_id,
            'invoice_number': sale['invoice_number'],
            'customer_id': customer_id,
            'return_date': return_date_str,
            'old_total_value': old_total_value,
            'new_total_value': new_total_value,
            'price_difference': price_difference,
            'payment_status': 'CUSTOMER_OWES' if price_difference > 0 else ('STORE_OWES' if price_difference < 0 else 'EVEN_EXCHANGE'),
            'old_items': validated_old_items,
            'new_items': validated_new_items
        }

    except Exception as e:
        conn.rollback()
        logger.error(f"Transaction failed during exchange: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
