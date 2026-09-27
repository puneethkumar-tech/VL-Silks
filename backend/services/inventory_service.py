import logging
from decimal import Decimal
from backend.utils.database import get_db_connection, query_db

logger = logging.getLogger('vl_silks.inventory_service')


class ValidationError(Exception):
    """Custom exception for inventory business validation errors."""
    pass


def get_inventory(search=None, category_id=None, status=None, stock_status=None):
    """
    Fetch all garment variants with product and category metadata, current stock quantity,
    minimum stock threshold, pricing, and computed stock status (IN_STOCK, LOW_STOCK, OUT_OF_STOCK).
    """
    sql = """
        SELECT 
            pv.variant_id,
            pv.product_id,
            p.product_name,
            p.brand,
            p.material,
            p.status AS product_status,
            c.category_id,
            c.category_name,
            pv.sku,
            pv.size,
            pv.color,
            pv.barcode,
            pv.purchase_price,
            pv.selling_price,
            pv.stock_quantity,
            pv.minimum_stock,
            pv.status AS variant_status,
            pv.updated_at,
            CASE 
                WHEN pv.stock_quantity = 0 THEN 'OUT_OF_STOCK'
                WHEN pv.stock_quantity <= pv.minimum_stock THEN 'LOW_STOCK'
                ELSE 'IN_STOCK'
            END AS stock_status
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE 1=1
    """
    params = []

    if category_id:
        sql += " AND p.category_id = %s"
        params.append(category_id)

    if status and status.upper() != 'ALL':
        sql += " AND pv.status = %s"
        params.append(status.upper())

    if stock_status and stock_status.upper() != 'ALL':
        st = stock_status.upper()
        if st == 'IN_STOCK':
            sql += " AND pv.stock_quantity > pv.minimum_stock"
        elif st == 'LOW_STOCK':
            sql += " AND pv.stock_quantity > 0 AND pv.stock_quantity <= pv.minimum_stock"
        elif st == 'OUT_OF_STOCK':
            sql += " AND pv.stock_quantity = 0"

    if search:
        search_term = f"%{search.strip()}%"
        sql += """ AND (
            p.product_name LIKE %s 
            OR p.brand LIKE %s 
            OR pv.sku LIKE %s 
            OR pv.barcode LIKE %s 
            OR pv.color LIKE %s 
            OR pv.size LIKE %s
            OR c.category_name LIKE %s
        )"""
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term, search_term])

    sql += " ORDER BY p.product_name ASC, pv.sku ASC"
    return query_db(sql, tuple(params))


def get_inventory_summary_metrics():
    """
    Calculate aggregate inventory health metrics from product_variants.
    - Total distinct variants
    - Total units on hand
    - In stock variant count
    - Low stock variant count
    - Out of stock variant count
    - Total inventory cost value (Sum of stock_quantity * purchase_price)
    - Total inventory retail value (Sum of stock_quantity * selling_price)
    """
    sql = """
        SELECT 
            COUNT(pv.variant_id) AS total_variants,
            COALESCE(SUM(pv.stock_quantity), 0) AS total_units,
            COUNT(CASE WHEN pv.stock_quantity > pv.minimum_stock THEN 1 END) AS in_stock_count,
            COUNT(CASE WHEN pv.stock_quantity > 0 AND pv.stock_quantity <= pv.minimum_stock THEN 1 END) AS low_stock_count,
            COUNT(CASE WHEN pv.stock_quantity = 0 THEN 1 END) AS out_of_stock_count,
            COALESCE(SUM(pv.stock_quantity * pv.purchase_price), 0) AS total_cost_value,
            COALESCE(SUM(pv.stock_quantity * pv.selling_price), 0) AS total_retail_value
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        WHERE pv.status = 'ACTIVE' AND p.status = 'ACTIVE'
    """
    row = query_db(sql, one=True) or {}
    return {
        'total_variants': row.get('total_variants', 0) or 0,
        'total_units': int(row.get('total_units', 0) or 0),
        'in_stock_count': row.get('in_stock_count', 0) or 0,
        'low_stock_count': row.get('low_stock_count', 0) or 0,
        'out_of_stock_count': row.get('out_of_stock_count', 0) or 0,
        'total_cost_value': Decimal(str(row.get('total_cost_value', '0.00'))),
        'total_retail_value': Decimal(str(row.get('total_retail_value', '0.00')))
    }


def get_low_stock_items():
    """
    Fetch all active variants where stock_quantity is positive but at or below minimum_stock threshold.
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
            pv.stock_quantity,
            pv.minimum_stock,
            (pv.minimum_stock - pv.stock_quantity) AS units_needed,
            pv.status AS variant_status,
            'LOW_STOCK' AS stock_status
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE pv.stock_quantity > 0 
          AND pv.stock_quantity <= pv.minimum_stock
          AND pv.status = 'ACTIVE' 
          AND p.status = 'ACTIVE'
        ORDER BY pv.stock_quantity ASC, p.product_name ASC
    """
    return query_db(sql)


def get_out_of_stock_items():
    """
    Fetch all active variants where stock_quantity is exactly zero.
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
            pv.stock_quantity,
            pv.minimum_stock,
            pv.status AS variant_status,
            'OUT_OF_STOCK' AS stock_status
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE pv.stock_quantity = 0
          AND pv.status = 'ACTIVE' 
          AND p.status = 'ACTIVE'
        ORDER BY p.product_name ASC, pv.sku ASC
    """
    return query_db(sql)


def get_stock_movements(variant_id=None, movement_type=None, reference_type=None, date_from=None, date_to=None, search=None, limit=200):
    """
    Fetch chronological stock movement audit logs joined with variant, product, and user details.
    """
    sql = """
        SELECT 
            sm.movement_id,
            sm.variant_id,
            sm.movement_type,
            sm.quantity,
            sm.reference_type,
            sm.reference_id,
            sm.notes,
            sm.movement_date,
            sm.created_by,
            u.name AS created_by_name,
            pv.sku,
            pv.size,
            pv.color,
            pv.stock_quantity AS current_stock,
            p.product_id,
            p.product_name,
            c.category_name
        FROM stock_movements sm
        JOIN product_variants pv ON sm.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        JOIN users u ON sm.created_by = u.user_id
        WHERE 1=1
    """
    params = []

    if variant_id:
        sql += " AND sm.variant_id = %s"
        params.append(variant_id)

    if movement_type and movement_type.upper() != 'ALL':
        sql += " AND sm.movement_type = %s"
        params.append(movement_type.upper())

    if reference_type and reference_type.upper() != 'ALL':
        sql += " AND sm.reference_type = %s"
        params.append(reference_type.upper())

    if date_from:
        sql += " AND sm.movement_date >= %s"
        params.append(f"{date_from} 00:00:00")

    if date_to:
        sql += " AND sm.movement_date <= %s"
        params.append(f"{date_to} 23:59:59")

    if search:
        search_term = f"%{search.strip()}%"
        sql += """ AND (
            p.product_name LIKE %s 
            OR pv.sku LIKE %s 
            OR sm.notes LIKE %s
            OR u.name LIKE %s
        )"""
        params.extend([search_term, search_term, search_term, search_term])

    sql += " ORDER BY sm.movement_date DESC, sm.movement_id DESC"
    if limit and isinstance(limit, int) and limit > 0:
        sql += f" LIMIT {limit}"

    return query_db(sql, tuple(params))


def adjust_stock(variant_id, adjustment_type, quantity, reason, user_id):
    """
    Atomically adjust variant inventory stock (INCREASE or DECREASE) and write an audit movement.
    
    Rules:
      - variant_id must exist and be ACTIVE.
      - adjustment_type must be 'INCREASE' or 'DECREASE'.
      - quantity must be an integer > 0.
      - reason is required and non-empty.
      - decrease cannot exceed current stock quantity.
      - stock_quantity cannot become negative.
    """
    # 1. Validation
    if not variant_id:
        raise ValidationError("Product variant is required.")
    try:
        variant_id = int(variant_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid variant ID.")

    if not adjustment_type or adjustment_type.upper() not in ('INCREASE', 'DECREASE'):
        raise ValidationError("Adjustment type must be either 'INCREASE' or 'DECREASE'.")
    adjustment_type = adjustment_type.upper()

    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        raise ValidationError("Adjustment quantity must be a valid integer.")
    if quantity <= 0:
        raise ValidationError("Adjustment quantity must be greater than zero.")

    reason = (reason or '').strip()
    if not reason:
        raise ValidationError("Adjustment reason / remark is required.")

    if not user_id:
        raise ValidationError("User ID is required for stock adjustment.")

    # 2. Atomic Transaction
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Fetch current variant state with lock
        cursor.execute("""
            SELECT 
                pv.variant_id, 
                pv.sku, 
                pv.stock_quantity, 
                pv.status AS variant_status,
                p.product_name, 
                p.status AS product_status
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.product_id
            WHERE pv.variant_id = %s
            FOR UPDATE
        """, (variant_id,))
        variant = cursor.fetchone()

        if not variant:
            raise ValidationError(f"Variant ID {variant_id} does not exist.")
        if variant['variant_status'] != 'ACTIVE' or variant['product_status'] != 'ACTIVE':
            raise ValidationError(f"Variant '{variant['sku']}' ({variant['product_name']}) is inactive and cannot be adjusted.")

        current_stock = variant['stock_quantity']

        if adjustment_type == 'INCREASE':
            delta = quantity
            new_stock = current_stock + quantity
        else:  # DECREASE
            if current_stock < quantity:
                raise ValidationError(f"Cannot decrease stock by {quantity} units. Current stock for '{variant['sku']}' is only {current_stock} units.")
            delta = -quantity
            new_stock = current_stock - quantity

        if new_stock < 0:
            raise ValidationError(f"Resulting stock ({new_stock}) cannot be negative.")

        # Update Stock
        cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = %s", (new_stock, variant_id))
        if cursor.rowcount == 0:
            raise Exception("Failed to update stock quantity.")

        # Insert Stock Movement
        movement_notes = f"Manual adjustment ({adjustment_type.lower()}): {reason}"
        cursor.execute("""
            INSERT INTO stock_movements (
                variant_id,
                movement_type,
                quantity,
                reference_type,
                reference_id,
                notes,
                created_by
            ) VALUES (%s, 'ADJUSTMENT', %s, 'MANUAL_ADJUSTMENT', NULL, %s, %s)
        """, (variant_id, delta, movement_notes, user_id))

        connection.commit()
        logger.info(f"Manual stock adjustment on variant #{variant_id} ({variant['sku']}): {current_stock} -> {new_stock} ({delta:+d}).")
        return {
            'variant_id': variant_id,
            'sku': variant['sku'],
            'product_name': variant['product_name'],
            'previous_stock': current_stock,
            'delta': delta,
            'new_stock': new_stock,
            'movement_type': 'ADJUSTMENT'
        }

    except Exception as e:
        connection.rollback()
        logger.error(f"Transaction failed during stock adjustment: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Stock adjustment failed: {str(e)}")
    finally:
        cursor.close()
        connection.close()


def record_damaged_stock(variant_id, quantity, reason, user_id):
    """
    Atomically record damaged or unsellable stock write-off, decreasing stock
    and inserting a stock movement with movement_type 'DAMAGE'.
    """
    if not variant_id:
        raise ValidationError("Product variant is required.")
    try:
        variant_id = int(variant_id)
    except (ValueError, TypeError):
        raise ValidationError("Invalid variant ID.")

    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        raise ValidationError("Damaged quantity must be a valid integer.")
    if quantity <= 0:
        raise ValidationError("Damaged quantity must be greater than zero.")

    reason = (reason or '').strip()
    if not reason:
        raise ValidationError("Damage reason / inspection note is required.")

    if not user_id:
        raise ValidationError("User ID is required for recording damaged stock.")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT 
                pv.variant_id, 
                pv.sku, 
                pv.stock_quantity, 
                pv.status AS variant_status,
                p.product_name, 
                p.status AS product_status
            FROM product_variants pv
            JOIN products p ON pv.product_id = p.product_id
            WHERE pv.variant_id = %s
            FOR UPDATE
        """, (variant_id,))
        variant = cursor.fetchone()

        if not variant:
            raise ValidationError(f"Variant ID {variant_id} does not exist.")
        if variant['variant_status'] != 'ACTIVE' or variant['product_status'] != 'ACTIVE':
            raise ValidationError(f"Variant '{variant['sku']}' ({variant['product_name']}) is inactive.")

        current_stock = variant['stock_quantity']
        if current_stock < quantity:
            raise ValidationError(f"Cannot write off {quantity} damaged units. Current stock for '{variant['sku']}' is only {current_stock} units.")

        new_stock = current_stock - quantity

        # Update stock
        cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = %s", (new_stock, variant_id))
        if cursor.rowcount == 0:
            raise Exception("Failed to update stock quantity.")

        # Insert movement with movement_type 'DAMAGE' and negative quantity
        movement_notes = f"Damaged stock write-off: {reason}"
        cursor.execute("""
            INSERT INTO stock_movements (
                variant_id,
                movement_type,
                quantity,
                reference_type,
                reference_id,
                notes,
                created_by
            ) VALUES (%s, 'DAMAGE', %s, 'MANUAL_ADJUSTMENT', NULL, %s, %s)
        """, (variant_id, -quantity, movement_notes, user_id))

        connection.commit()
        logger.info(f"Damaged stock recorded for variant #{variant_id} ({variant['sku']}): {current_stock} -> {new_stock} (-{quantity}).")
        return {
            'variant_id': variant_id,
            'sku': variant['sku'],
            'product_name': variant['product_name'],
            'previous_stock': current_stock,
            'damaged_quantity': quantity,
            'new_stock': new_stock,
            'movement_type': 'DAMAGE'
        }

    except Exception as e:
        connection.rollback()
        logger.error(f"Transaction failed during damaged stock recording: {e}")
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to record damaged stock: {str(e)}")
    finally:
        cursor.close()
        connection.close()
