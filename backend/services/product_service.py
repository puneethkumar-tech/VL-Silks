import logging
from backend.utils.database import get_db_cursor, query_db

logger = logging.getLogger('vl_silks.product_service')

class ValidationError(Exception):
    """Custom exception for business validation errors."""
    pass

def get_all_categories(status='ACTIVE'):
    """Fetch list of categories for dropdowns and filtering."""
    if status:
        return query_db(
            "SELECT category_id, category_name, description, status FROM categories WHERE status = %s ORDER BY category_name ASC",
            (status,)
        )
    return query_db(
        "SELECT category_id, category_name, description, status FROM categories ORDER BY category_name ASC"
    )

def get_all_products(search=None, category_id=None, status=None):
    """
    Fetch all products with aggregated variant count, total stock, and category info.
    Supports search across product_name, brand, sku, and barcode.
    """
    sql = """
        SELECT 
            p.product_id,
            p.product_name,
            p.brand,
            p.material,
            p.description,
            p.status,
            p.category_id,
            c.category_name,
            COUNT(pv.variant_id) AS variant_count,
            COALESCE(SUM(pv.stock_quantity), 0) AS total_stock,
            MIN(pv.selling_price) AS min_price,
            MAX(pv.selling_price) AS max_price,
            p.created_at,
            p.updated_at
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN product_variants pv ON p.product_id = pv.product_id
        WHERE 1=1
    """
    params = []

    if category_id:
        sql += " AND p.category_id = %s"
        params.append(category_id)

    if status and status.upper() != 'ALL':
        sql += " AND p.status = %s"
        params.append(status.upper())

    if search:
        search_term = f"%{search.strip()}%"
        sql += """ AND (
            p.product_name LIKE %s 
            OR p.brand LIKE %s 
            OR p.material LIKE %s
            OR p.product_id IN (
                SELECT DISTINCT product_id FROM product_variants 
                WHERE sku LIKE %s OR barcode LIKE %s OR color LIKE %s OR size LIKE %s
            )
        )"""
        params.extend([search_term, search_term, search_term, search_term, search_term, search_term, search_term])

    sql += " GROUP BY p.product_id, c.category_name ORDER BY p.product_id DESC"
    return query_db(sql, tuple(params))

def get_product_by_id(product_id):
    """Fetch single product by ID with category name."""
    sql = """
        SELECT 
            p.product_id,
            p.product_name,
            p.brand,
            p.material,
            p.description,
            p.status,
            p.category_id,
            c.category_name,
            p.created_at,
            p.updated_at
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.product_id = %s
    """
    return query_db(sql, (product_id,), one=True)

def get_product_variants(product_id, status=None):
    """
    Fetch all variants for a product and compute stock status.
    Stock status rules:
      - stock_quantity > minimum_stock -> IN STOCK
      - stock_quantity > 0 and <= minimum_stock -> LOW STOCK
      - stock_quantity = 0 -> OUT OF STOCK
    """
    sql = """
        SELECT 
            variant_id,
            product_id,
            sku,
            size,
            color,
            purchase_price,
            selling_price,
            stock_quantity,
            minimum_stock,
            barcode,
            status,
            created_at,
            updated_at
        FROM product_variants
        WHERE product_id = %s
    """
    params = [product_id]
    if status and status.upper() != 'ALL':
        sql += " AND status = %s"
        params.append(status.upper())

    sql += " ORDER BY variant_id ASC"
    variants = query_db(sql, tuple(params))

    # Enrich with stock status
    for v in variants:
        stock = v['stock_quantity']
        min_stock = v['minimum_stock']
        if stock > min_stock:
            v['stock_status'] = 'IN_STOCK'
            v['stock_status_label'] = 'In Stock'
            v['stock_status_badge'] = 'success'
        elif stock > 0:
            v['stock_status'] = 'LOW_STOCK'
            v['stock_status_label'] = 'Low Stock'
            v['stock_status_badge'] = 'warning'
        else:
            v['stock_status'] = 'OUT_OF_STOCK'
            v['stock_status_label'] = 'Out of Stock'
            v['stock_status_badge'] = 'danger'

    return variants

def get_variant_by_id(variant_id):
    """Fetch a single variant by ID."""
    sql = """
        SELECT 
            pv.*,
            p.product_name,
            p.category_id,
            c.category_name
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        JOIN categories c ON p.category_id = c.category_id
        WHERE pv.variant_id = %s
    """
    return query_db(sql, (variant_id,), one=True)

def validate_product_data(data):
    """Validate base product fields."""
    errors = []
    product_name = str(data.get('product_name') or '').strip()
    category_id = data.get('category_id')

    if not product_name:
        errors.append("Product name is required.")
    elif len(product_name) > 150:
        errors.append("Product name cannot exceed 150 characters.")

    if not category_id:
        errors.append("Category is required.")
    else:
        try:
            cat_id = int(category_id)
            cat = query_db("SELECT category_id FROM categories WHERE category_id = %s", (cat_id,), one=True)
            if not cat:
                errors.append("Selected category does not exist.")
        except (ValueError, TypeError):
            errors.append("Invalid category ID.")

    if errors:
        raise ValidationError("; ".join(errors))

def validate_variant_data(variant, existing_variant_id=None, seen_skus=None, seen_barcodes=None):
    """Validate individual variant fields and ensure SKU/barcode uniqueness."""
    errors = []
    sku = str(variant.get('sku') or '').strip()
    size = str(variant.get('size') or '').strip()
    color = str(variant.get('color') or '').strip()
    raw_barcode = variant.get('barcode')
    barcode = str(raw_barcode).strip() if raw_barcode is not None and str(raw_barcode).strip() else None

    if not sku:
        errors.append("Variant SKU is required.")
    elif len(sku) > 50:
        errors.append("Variant SKU cannot exceed 50 characters.")
    else:
        # Check uniqueness in current batch
        if seen_skus is not None:
            if sku.upper() in seen_skus:
                errors.append(f"Duplicate SKU '{sku}' within the same product submission.")
            seen_skus.add(sku.upper())

        # Check uniqueness in database
        check_sql = "SELECT variant_id FROM product_variants WHERE sku = %s"
        params = [sku]
        if existing_variant_id:
            check_sql += " AND variant_id != %s"
            params.append(existing_variant_id)
        if query_db(check_sql, tuple(params), one=True):
            errors.append(f"SKU '{sku}' already exists in the system. SKUs must be globally unique.")

    if not size:
        errors.append(f"Size is required for variant '{sku or 'New'}'")
    if not color:
        errors.append(f"Color is required for variant '{sku or 'New'}'")

    # Purchase price validation (optional, defaults to 0)
    raw_pp = variant.get('purchase_price')
    try:
        purchase_price = float(raw_pp if raw_pp is not None and str(raw_pp).strip() != '' else 0)
        if purchase_price < 0:
            errors.append(f"Purchase price cannot be negative for variant '{sku}'.")
    except (ValueError, TypeError):
        errors.append(f"Invalid purchase price for variant '{sku}'.")

    # Selling price validation (required)
    raw_sp = variant.get('selling_price')
    if raw_sp is None or str(raw_sp).strip() == '':
        errors.append(f"Selling price is required for variant '{sku or 'New'}'.")
    else:
        try:
            selling_price = float(raw_sp)
            if selling_price < 0:
                errors.append(f"Selling price cannot be negative for variant '{sku}'.")
        except (ValueError, TypeError):
            errors.append(f"Invalid selling price for variant '{sku}'.")

    # Minimum stock validation (optional, defaults to 5)
    raw_ms = variant.get('minimum_stock')
    try:
        minimum_stock = int(raw_ms if raw_ms is not None and str(raw_ms).strip() != '' else 5)
        if minimum_stock < 0:
            errors.append(f"Minimum stock cannot be negative for variant '{sku}'.")
    except (ValueError, TypeError):
        errors.append(f"Invalid minimum stock for variant '{sku}'.")

    # Opening stock validation if present (optional, defaults to 0)
    raw_sq = variant.get('stock_quantity')
    if raw_sq is not None and str(raw_sq).strip() != '':
        try:
            stock_qty = int(raw_sq)
            if stock_qty < 0:
                errors.append(f"Stock quantity cannot be negative for variant '{sku}'.")
        except (ValueError, TypeError):
            errors.append(f"Invalid stock quantity for variant '{sku}'.")

    # Barcode validation (optional)
    if barcode:
        if seen_barcodes is not None:
            if barcode in seen_barcodes:
                errors.append(f"Duplicate barcode '{barcode}' within the same submission.")
            seen_barcodes.add(barcode)

        bar_sql = "SELECT variant_id FROM product_variants WHERE barcode = %s"
        b_params = [barcode]
        if existing_variant_id:
            bar_sql += " AND variant_id != %s"
            b_params.append(existing_variant_id)
        if query_db(bar_sql, tuple(b_params), one=True):
            errors.append(f"Barcode '{barcode}' is already assigned to another variant.")

    if errors:
        raise ValidationError("; ".join(errors))

def create_product_with_variants(product_data, variants_data, user_id=None):
    """
    Atomic transaction to create a base product and its variants.
    """
    validate_product_data(product_data)

    if not variants_data or len(variants_data) == 0:
        raise ValidationError("At least one product variant (size/color/SKU) is required.")

    seen_skus = set()
    seen_barcodes = set()
    for v in variants_data:
        validate_variant_data(v, seen_skus=seen_skus, seen_barcodes=seen_barcodes)

    with get_db_cursor(commit=True) as cursor:
        # 1. Insert Base Product
        product_name = str(product_data.get('product_name') or '').strip()
        brand = str(product_data.get('brand') or 'VL Silks').strip() or 'VL Silks'
        material = str(product_data.get('material') or '').strip() or None
        description = str(product_data.get('description') or '').strip() or None
        status = str(product_data.get('status') or 'ACTIVE').strip() or 'ACTIVE'

        cursor.execute("""
            INSERT INTO products (category_id, product_name, brand, material, description, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            int(product_data['category_id']),
            product_name,
            brand,
            material,
            description,
            status
        ))
        product_id = cursor.lastrowid

        # 2. Insert Variants
        for v in variants_data:
            sku = str(v.get('sku') or '').strip()
            size = str(v.get('size') or '').strip()
            color = str(v.get('color') or '').strip()

            raw_pp = v.get('purchase_price')
            purchase_price = float(raw_pp if raw_pp is not None and str(raw_pp).strip() != '' else 0)

            raw_sp = v.get('selling_price')
            selling_price = float(raw_sp if raw_sp is not None and str(raw_sp).strip() != '' else 0)

            raw_stock = v.get('stock_quantity')
            stock_quantity = int(raw_stock if raw_stock is not None and str(raw_stock).strip() != '' else 0)

            raw_ms = v.get('minimum_stock')
            minimum_stock = int(raw_ms if raw_ms is not None and str(raw_ms).strip() != '' else 5)

            raw_barcode = v.get('barcode')
            barcode = str(raw_barcode).strip() if raw_barcode is not None and str(raw_barcode).strip() else None

            raw_status = v.get('status')
            status = str(raw_status).strip() if raw_status is not None and str(raw_status).strip() else 'ACTIVE'

            cursor.execute("""
                INSERT INTO product_variants 
                (product_id, sku, size, color, purchase_price, selling_price, stock_quantity, minimum_stock, barcode, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product_id, sku, size, color, purchase_price, selling_price,
                max(0, stock_quantity), max(0, minimum_stock), barcode, status
            ))
            variant_id = cursor.lastrowid

            # If opening stock was specified (> 0) and user provided, record opening stock movement
            if stock_quantity > 0 and user_id:
                cursor.execute("""
                    INSERT INTO stock_movements 
                    (variant_id, movement_type, quantity, reference_type, notes, created_by)
                    VALUES (%s, 'OPENING', %s, 'MANUAL_ADJUSTMENT', 'Initial opening stock upon product creation', %s)
                """, (variant_id, stock_quantity, user_id))

        return product_id

def update_product(product_id, product_data):
    """
    Update base product details.
    """
    validate_product_data(product_data)
    with get_db_cursor(commit=True) as cursor:
        product_name = str(product_data.get('product_name') or '').strip()
        brand = str(product_data.get('brand') or 'VL Silks').strip() or 'VL Silks'
        material = str(product_data.get('material') or '').strip() or None
        description = str(product_data.get('description') or '').strip() or None
        status = str(product_data.get('status') or 'ACTIVE').strip() or 'ACTIVE'

        cursor.execute("""
            UPDATE products
            SET category_id = %s,
                product_name = %s,
                brand = %s,
                material = %s,
                description = %s,
                status = %s
            WHERE product_id = %s
        """, (
            int(product_data['category_id']),
            product_name,
            brand,
            material,
            description,
            status,
            product_id
        ))
        return cursor.rowcount > 0

def update_variant(variant_id, variant_data):
    """
    Update an existing variant's metadata, prices, minimum stock, and status.
    IMPORTANT: stock_quantity is NOT modified directly here to maintain audit integrity.
    """
    validate_variant_data(variant_data, existing_variant_id=variant_id)
    with get_db_cursor(commit=True) as cursor:
        sku = str(variant_data.get('sku') or '').strip()
        size = str(variant_data.get('size') or '').strip()
        color = str(variant_data.get('color') or '').strip()

        raw_pp = variant_data.get('purchase_price')
        purchase_price = float(raw_pp if raw_pp is not None and str(raw_pp).strip() != '' else 0)

        raw_sp = variant_data.get('selling_price')
        selling_price = float(raw_sp if raw_sp is not None and str(raw_sp).strip() != '' else 0)

        raw_ms = variant_data.get('minimum_stock')
        minimum_stock = int(raw_ms if raw_ms is not None and str(raw_ms).strip() != '' else 5)

        raw_barcode = variant_data.get('barcode')
        barcode = str(raw_barcode).strip() if raw_barcode is not None and str(raw_barcode).strip() else None

        raw_status = variant_data.get('status')
        status = str(raw_status).strip() if raw_status is not None and str(raw_status).strip() else 'ACTIVE'

        cursor.execute("""
            UPDATE product_variants
            SET sku = %s,
                size = %s,
                color = %s,
                purchase_price = %s,
                selling_price = %s,
                minimum_stock = %s,
                barcode = %s,
                status = %s
            WHERE variant_id = %s
        """, (
            sku,
            size,
            color,
            purchase_price,
            selling_price,
            minimum_stock,
            barcode,
            status,
            variant_id
        ))
        return cursor.rowcount > 0

def add_variant_to_product(product_id, variant_data, user_id=None):
    """
    Add a new variant to an existing product.
    """
    product = get_product_by_id(product_id)
    if not product:
        raise ValidationError("Product not found.")

    validate_variant_data(variant_data)
    with get_db_cursor(commit=True) as cursor:
        sku = str(variant_data.get('sku') or '').strip()
        size = str(variant_data.get('size') or '').strip()
        color = str(variant_data.get('color') or '').strip()

        raw_pp = variant_data.get('purchase_price')
        purchase_price = float(raw_pp if raw_pp is not None and str(raw_pp).strip() != '' else 0)

        raw_sp = variant_data.get('selling_price')
        selling_price = float(raw_sp if raw_sp is not None and str(raw_sp).strip() != '' else 0)

        raw_stock = variant_data.get('stock_quantity')
        stock_quantity = int(raw_stock if raw_stock is not None and str(raw_stock).strip() != '' else 0)

        raw_ms = variant_data.get('minimum_stock')
        minimum_stock = int(raw_ms if raw_ms is not None and str(raw_ms).strip() != '' else 5)

        raw_barcode = variant_data.get('barcode')
        barcode = str(raw_barcode).strip() if raw_barcode is not None and str(raw_barcode).strip() else None

        raw_status = variant_data.get('status')
        status = str(raw_status).strip() if raw_status is not None and str(raw_status).strip() else 'ACTIVE'

        cursor.execute("""
            INSERT INTO product_variants 
            (product_id, sku, size, color, purchase_price, selling_price, stock_quantity, minimum_stock, barcode, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            product_id, sku, size, color, purchase_price, selling_price,
            max(0, stock_quantity), max(0, minimum_stock), barcode, status
        ))
        variant_id = cursor.lastrowid

        if stock_quantity > 0 and user_id:
            cursor.execute("""
                INSERT INTO stock_movements 
                (variant_id, movement_type, quantity, reference_type, notes, created_by)
                VALUES (%s, 'OPENING', %s, 'MANUAL_ADJUSTMENT', 'Initial opening stock upon variant creation', %s)
            """, (variant_id, stock_quantity, user_id))

        return variant_id

def toggle_product_status(product_id, new_status=None):
    """
    Toggle or set product status (ACTIVE / INACTIVE).
    """
    product = get_product_by_id(product_id)
    if not product:
        raise ValidationError("Product not found.")

    if not new_status:
        new_status = 'INACTIVE' if product['status'] == 'ACTIVE' else 'ACTIVE'

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE products SET status = %s WHERE product_id = %s", (new_status, product_id))
        # When deactivating product, also deactivate all its variants
        if new_status == 'INACTIVE':
            cursor.execute("UPDATE product_variants SET status = 'INACTIVE' WHERE product_id = %s", (product_id,))
        return new_status

def toggle_variant_status(variant_id, new_status=None):
    """
    Toggle or set variant status (ACTIVE / INACTIVE).
    """
    variant = get_variant_by_id(variant_id)
    if not variant:
        raise ValidationError("Variant not found.")

    if not new_status:
        new_status = 'INACTIVE' if variant['status'] == 'ACTIVE' else 'ACTIVE'

    with get_db_cursor(commit=True) as cursor:
        cursor.execute("UPDATE product_variants SET status = %s WHERE variant_id = %s", (new_status, variant_id))
        return new_status
