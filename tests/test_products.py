import pytest
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import product_service
from backend.services.product_service import ValidationError

@pytest.fixture
def app():
    """Create test app instance."""
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()

@pytest.fixture
def admin_client(client):
    """Client logged in as Admin."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Venkata Lakshmi (Admin)'
        sess['user_email'] = 'admin@vlsilks.com'
        sess['user_role'] = 'ADMIN'
    return client

@pytest.fixture
def staff_client(client):
    """Client logged in as Staff."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Kiran Kumar (Staff)'
        sess['user_email'] = 'staff@vlsilks.com'
        sess['user_role'] = 'STAFF'
    return client


# ---------------------------------------------------------------------------
# 1. Product List & Filtering Tests
# ---------------------------------------------------------------------------
def test_get_all_products(app):
    """Test retrieving products list."""
    with app.app_context():
        products = product_service.get_all_products()
        assert len(products) > 0
        p = products[0]
        assert 'product_name' in p
        assert 'category_name' in p
        assert 'variant_count' in p
        assert 'total_stock' in p

def test_product_search(app):
    """Test search across product name, SKU, and brand."""
    with app.app_context():
        # Search by name
        res1 = product_service.get_all_products(search='Saree')
        assert len(res1) > 0

        # Search by SKU
        res2 = product_service.get_all_products(search='SKU-KAN-RED')
        assert len(res2) >= 1
        assert any('Kanchipuram' in p['product_name'] for p in res2)

        # Search by non-existent term
        res3 = product_service.get_all_products(search='NON_EXISTENT_XYZ_123')
        assert len(res3) == 0

def test_product_category_filter(app):
    """Test filtering products by category ID."""
    with app.app_context():
        # Filter by Sarees category (id 1)
        sarees = product_service.get_all_products(category_id=1)
        assert len(sarees) > 0
        for s in sarees:
            assert s['category_id'] == 1


# ---------------------------------------------------------------------------
# 2. Product Creation with Multiple Variants
# ---------------------------------------------------------------------------
def test_create_product_with_multiple_variants(app):
    """Test creating a base product along with multiple variants in one atomic transaction."""
    with app.app_context():
        product_data = {
            'product_name': 'Test Mysore Silk Saree',
            'category_id': 1,
            'brand': 'VL Silks Premium',
            'material': 'Pure Silk',
            'description': 'Handwoven pure Mysore silk test garment',
            'status': 'ACTIVE'
        }
        variants_data = [
            {
                'sku': 'SKU-MYS-RED-01',
                'size': 'Free Size',
                'color': 'Ruby Red',
                'purchase_price': 5000.00,
                'selling_price': 7999.00,
                'stock_quantity': 10,
                'minimum_stock': 2,
                'barcode': '9900112201'
            },
            {
                'sku': 'SKU-MYS-GLD-02',
                'size': 'Free Size',
                'color': 'Antique Gold',
                'purchase_price': 5200.00,
                'selling_price': 8499.00,
                'stock_quantity': 5,
                'minimum_stock': 2,
                'barcode': '9900112202'
            }
        ]

        product_id = product_service.create_product_with_variants(product_data, variants_data, user_id=1)
        assert product_id > 0

        # Verify product and variants
        p = product_service.get_product_by_id(product_id)
        assert p['product_name'] == 'Test Mysore Silk Saree'

        variants = product_service.get_product_variants(product_id)
        assert len(variants) == 2
        skus = [v['sku'] for v in variants]
        assert 'SKU-MYS-RED-01' in skus
        assert 'SKU-MYS-GLD-02' in skus

        # Cleanup test records safely
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE variant_id IN (%s, %s)", (variants[0]['variant_id'], variants[1]['variant_id']))
            cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (product_id,))
            cursor.execute("DELETE FROM products WHERE product_id = %s", (product_id,))


# ---------------------------------------------------------------------------
# 3. Validation & Constraint Tests
# ---------------------------------------------------------------------------
def test_duplicate_sku_rejection(app):
    """Test that duplicate SKU is rejected both in batch and in database."""
    with app.app_context():
        # Batch duplicate test
        product_data = {'product_name': 'Test Batch Dup', 'category_id': 1}
        variants_batch_dup = [
            {'sku': 'SKU-DUP-TEST', 'size': 'M', 'color': 'Red', 'purchase_price': 100, 'selling_price': 200},
            {'sku': 'SKU-DUP-TEST', 'size': 'L', 'color': 'Blue', 'purchase_price': 100, 'selling_price': 200}
        ]
        with pytest.raises(ValidationError) as exc:
            product_service.create_product_with_variants(product_data, variants_batch_dup)
        assert 'Duplicate SKU' in str(exc.value)

        # Existing DB duplicate test (SKU-KAN-RED already exists in seed)
        variants_db_dup = [
            {'sku': 'SKU-KAN-RED', 'size': 'M', 'color': 'Red', 'purchase_price': 100, 'selling_price': 200}
        ]
        with pytest.raises(ValidationError) as exc2:
            product_service.create_product_with_variants(product_data, variants_db_dup)
        assert 'already exists' in str(exc2.value)

def test_duplicate_barcode_rejection(app):
    """Test that duplicate barcode is rejected."""
    with app.app_context():
        product_data = {'product_name': 'Test Barcode Dup', 'category_id': 1}
        # Barcode 8901001001 exists on SKU-KAN-RED
        variants = [
            {'sku': 'SKU-UNIQUE-NEW-1', 'size': 'M', 'color': 'Red', 'purchase_price': 100, 'selling_price': 200, 'barcode': '8901001001'}
        ]
        with pytest.raises(ValidationError) as exc:
            product_service.create_product_with_variants(product_data, variants)
        assert 'Barcode' in str(exc.value) and 'already assigned' in str(exc.value)

def test_invalid_category_rejection(app):
    """Test that non-existent category ID is rejected."""
    with app.app_context():
        product_data = {'product_name': 'Test Invalid Cat', 'category_id': 99999}
        variants = [{'sku': 'SKU-CAT-TEST', 'size': 'M', 'color': 'Red', 'purchase_price': 100, 'selling_price': 200}]
        with pytest.raises(ValidationError) as exc:
            product_service.create_product_with_variants(product_data, variants)
        assert 'category' in str(exc.value).lower()

def test_negative_values_rejection(app):
    """Test that negative prices and negative minimum stock are rejected."""
    with app.app_context():
        product_data = {'product_name': 'Test Neg Val', 'category_id': 1}
        
        # Negative purchase price
        with pytest.raises(ValidationError):
            product_service.create_product_with_variants(product_data, [
                {'sku': 'SKU-NEG-1', 'size': 'M', 'color': 'Red', 'purchase_price': -50, 'selling_price': 100}
            ])

        # Negative selling price
        with pytest.raises(ValidationError):
            product_service.create_product_with_variants(product_data, [
                {'sku': 'SKU-NEG-2', 'size': 'M', 'color': 'Red', 'purchase_price': 50, 'selling_price': -100}
            ])

        # Negative minimum stock
        with pytest.raises(ValidationError):
            product_service.create_product_with_variants(product_data, [
                {'sku': 'SKU-NEG-3', 'size': 'M', 'color': 'Red', 'purchase_price': 50, 'selling_price': 100, 'minimum_stock': -5}
            ])


# ---------------------------------------------------------------------------
# 4. Product & Variant Updates and Stock Safety
# ---------------------------------------------------------------------------
def test_product_update_and_stock_safety(app):
    """Test updating product and variant, verifying stock_quantity is preserved."""
    with app.app_context():
        # Check initial state of product 1 and variant 1
        v_before = product_service.get_variant_by_id(1)
        initial_stock = v_before['stock_quantity']

        # Update base product
        product_service.update_product(1, {
            'product_name': 'Kanchipuram Pure Zari Silk Saree (Heritage Edition)',
            'category_id': 1,
            'brand': 'VL Silks Heritage',
            'material': '100% Pure Mulberry Silk',
            'description': 'Updated weaving description',
            'status': 'ACTIVE'
        })
        p_after = product_service.get_product_by_id(1)
        assert p_after['product_name'] == 'Kanchipuram Pure Zari Silk Saree (Heritage Edition)'

        # Update variant 1 selling price and min stock
        product_service.update_variant(1, {
            'sku': v_before['sku'],
            'size': v_before['size'],
            'color': 'Crimson Red / 24K Gold Zari',
            'purchase_price': v_before['purchase_price'],
            'selling_price': 10999.00,
            'minimum_stock': 4,
            'barcode': v_before['barcode'],
            'status': 'ACTIVE'
        })
        v_after = product_service.get_variant_by_id(1)
        assert v_after['selling_price'] == 10999.00
        assert v_after['minimum_stock'] == 4
        # CRITICAL CHECK: stock_quantity must remain unchanged!
        assert v_after['stock_quantity'] == initial_stock

def test_variant_stock_status_labels(app):
    """Test calculation of IN_STOCK, LOW_STOCK, and OUT_OF_STOCK statuses."""
    with app.app_context():
        variants = product_service.get_product_variants(2)  # Banarasi saree
        assert len(variants) > 0

        # Verify the status labels are correctly derived from live stock values
        for v in variants:
            stock = v['stock_quantity']
            min_stock = v.get('minimum_stock', 0) or 0
            if stock == 0:
                expected = 'OUT_OF_STOCK'
                expected_badge = 'danger'
            elif stock <= min_stock:
                expected = 'LOW_STOCK'
                expected_badge = 'warning'
            else:
                expected = 'IN_STOCK'
                expected_badge = 'success'
            assert v['stock_status'] == expected, (
                f"Variant {v['variant_id']}: stock={stock}, min={min_stock}, "
                f"expected {expected} but got {v['stock_status']}"
            )
            assert v['stock_status_badge'] == expected_badge


# ---------------------------------------------------------------------------
# 5. Status Deactivation & Consistency Regressions
# ---------------------------------------------------------------------------
def test_product_and_variant_status_toggle(app):
    """Test deactivating a product and variant using an isolated temporary product."""
    with app.app_context():
        import time
        ts = int(time.time() * 1000)
        temp_sku = f"SKU-TOGGLE-TEST-{ts}"
        pid = product_service.create_product_with_variants(
            {
                'product_name': f'Temp Toggle Product {ts}',
                'category_id': 1,
                'brand': 'VL Silks',
                'material': 'Silk',
                'description': 'Temporary test product',
                'status': 'ACTIVE'
            },
            [{
                'sku': temp_sku,
                'size': 'Free Size',
                'color': 'Ruby Red',
                'purchase_price': 1000.0,
                'selling_price': 2000.0,
                'stock_quantity': 5,
                'minimum_stock': 2,
                'status': 'ACTIVE'
            }],
            user_id=1
        )
        try:
            # 1. Toggle product to INACTIVE
            product_service.toggle_product_status(pid, 'INACTIVE')
            p = product_service.get_product_by_id(pid)
            assert p['status'] == 'INACTIVE'
            vars_inactive = product_service.get_product_variants(pid)
            assert all(v['status'] == 'INACTIVE' for v in vars_inactive)

            # 2. Toggle product back to ACTIVE
            product_service.toggle_product_status(pid, 'ACTIVE')
            p_restored = product_service.get_product_by_id(pid)
            assert p_restored['status'] == 'ACTIVE'

            # 3. Toggle single variant status
            vid = vars_inactive[0]['variant_id']
            product_service.toggle_variant_status(vid, 'ACTIVE')
            v_active = product_service.get_variant_by_id(vid)
            assert v_active['status'] == 'ACTIVE'
            product_service.toggle_variant_status(vid, 'INACTIVE')
            v_inact = product_service.get_variant_by_id(vid)
            assert v_inact['status'] == 'INACTIVE'
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE variant_id IN (SELECT variant_id FROM product_variants WHERE product_id = %s)", (pid,))
                cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (pid,))
                cursor.execute("DELETE FROM products WHERE product_id = %s", (pid,))


def test_variant_status_independent_of_stock_levels(app):
    """Regression: Low stock and zero stock must NOT change variant status from ACTIVE."""
    with app.app_context():
        import time
        ts = int(time.time() * 1000)
        temp_sku = f"SKU-STOCK-TEST-{ts}"
        pid = product_service.create_product_with_variants(
            {
                'product_name': f'Stock Status Independence Test {ts}',
                'category_id': 1,
                'brand': 'VL Silks',
                'material': 'Silk',
                'status': 'ACTIVE'
            },
            [{
                'sku': temp_sku,
                'size': 'Free Size',
                'color': 'Blue',
                'purchase_price': 500.0,
                'selling_price': 900.0,
                'stock_quantity': 10,
                'minimum_stock': 3,
                'status': 'ACTIVE'
            }],
            user_id=1
        )
        try:
            variants = product_service.get_product_variants(pid)
            vid = variants[0]['variant_id']
            assert variants[0]['stock_status'] == 'IN_STOCK'
            assert variants[0]['status'] == 'ACTIVE'

            # 1. Update stock to LOW STOCK level (stock = 2, min_stock = 3)
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("UPDATE product_variants SET stock_quantity = 2 WHERE variant_id = %s", (vid,))

            v_low = product_service.get_product_variants(pid)[0]
            assert v_low['stock_status'] == 'LOW_STOCK'
            assert v_low['status'] == 'ACTIVE', "LOW STOCK must NOT set variant status to INACTIVE!"

            # 2. Update stock to OUT OF STOCK level (stock = 0)
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("UPDATE product_variants SET stock_quantity = 0 WHERE variant_id = %s", (vid,))

            v_zero = product_service.get_product_variants(pid)[0]
            assert v_zero['stock_status'] == 'OUT_OF_STOCK'
            assert v_zero['status'] == 'ACTIVE', "OUT OF STOCK must NOT set catalog status to INACTIVE!"

            # 3. Update unrelated variant metadata (prices, barcode, min_stock)
            product_service.update_variant(vid, {
                'sku': temp_sku,
                'size': 'L',
                'color': 'Royal Navy',
                'purchase_price': 550.0,
                'selling_price': 950.0,
                'minimum_stock': 5,
                'barcode': f'BAR{ts}',
                'status': 'ACTIVE'
            })
            v_meta = product_service.get_product_variants(pid)[0]
            assert v_meta['selling_price'] == 950.0
            assert v_meta['status'] == 'ACTIVE'
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE variant_id IN (SELECT variant_id FROM product_variants WHERE product_id = %s)", (pid,))
                cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (pid,))
                cursor.execute("DELETE FROM products WHERE product_id = %s", (pid,))


def test_product_edit_flow_preserves_variant_status(app, admin_client):
    """Regression: Submitting base garment edit and variant edit preserves ACTIVE status."""
    with app.app_context():
        import time
        ts = int(time.time() * 1000)
        temp_sku = f"SKU-EDIT-FLOW-{ts}"
        pid = product_service.create_product_with_variants(
            {
                'product_name': f'Edit Flow Saree {ts}',
                'category_id': 1,
                'brand': 'VL Silks',
                'material': 'Silk',
                'status': 'ACTIVE'
            },
            [{
                'sku': temp_sku,
                'size': 'Free Size',
                'color': 'Gold',
                'purchase_price': 600.0,
                'selling_price': 1200.0,
                'stock_quantity': 1,
                'minimum_stock': 2,
                'status': 'ACTIVE'
            }],
            user_id=1
        )
        try:
            variants = product_service.get_product_variants(pid)
            vid = variants[0]['variant_id']
            assert variants[0]['status'] == 'ACTIVE'

            # 1. Open edit page in browser/client
            res_get = admin_client.get(f'/products/{pid}/edit')
            assert res_get.status_code == 200

            # 2. Submit base garment update via POST
            res_post_base = admin_client.post(f'/products/{pid}/edit', data={
                'product_name': f'Edit Flow Saree Updated {ts}',
                'category_id': '1',
                'brand': 'VL Silks Premium',
                'material': 'Pure Silk',
                'description': 'Updated description',
                'status': 'ACTIVE'
            }, follow_redirects=True)
            assert res_post_base.status_code == 200

            # Verify variant remains ACTIVE
            v_after_base = product_service.get_variant_by_id(vid)
            assert v_after_base['status'] == 'ACTIVE', "Base product edit must NOT change variant status!"

            # 3. Submit variant update via POST (e.g. price change)
            res_post_var = admin_client.post(f'/products/variants/{vid}/edit', data={
                'sku': temp_sku,
                'size': 'Free Size',
                'color': 'Gold',
                'purchase_price': '650.00',
                'selling_price': '1250.00',
                'minimum_stock': '2',
                'barcode': '',
                'status': 'ACTIVE'
            }, follow_redirects=True)
            assert res_post_var.status_code == 200

            v_after_var = product_service.get_variant_by_id(vid)
            assert v_after_var['selling_price'] == 1250.00
            assert v_after_var['status'] == 'ACTIVE', "Variant edit must keep ACTIVE status!"
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE variant_id IN (SELECT variant_id FROM product_variants WHERE product_id = %s)", (pid,))
                cursor.execute("DELETE FROM product_variants WHERE product_id = %s", (pid,))
                cursor.execute("DELETE FROM products WHERE product_id = %s", (pid,))



# ---------------------------------------------------------------------------
# 6. Web Routes & Role Access Permissions
# ---------------------------------------------------------------------------
def test_web_routes_unauthenticated_redirects(client):
    """Unauthenticated users must be redirected to login."""
    res = client.get('/products')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']

def test_web_routes_staff_permissions(staff_client):
    """Staff can view product list & details, but cannot access /products/new or edit."""
    # Staff views products list
    res_list = staff_client.get('/products')
    assert res_list.status_code == 200
    assert b'Product Catalog' in res_list.data

    # Staff views product details
    res_view = staff_client.get('/products/1')
    assert res_view.status_code == 200
    assert b'Garment Details &amp; Variants' in res_view.data or b'Garment Details & Variants' in res_view.data

    # Staff tries to access add product -> redirected with error
    res_new = staff_client.get('/products/new', follow_redirects=True)
    assert b'Administrator access required' in res_new.data

def test_web_routes_admin_crud(admin_client):
    """Admin has full access to add, edit, and view."""
    res_new = admin_client.get('/products/new')
    assert res_new.status_code == 200
    assert b'Add New Garment Product' in res_new.data

    res_edit = admin_client.get('/products/1/edit')
    assert res_edit.status_code == 200
    assert b'Edit Garment &amp; Variants' in res_edit.data or b'Edit Garment & Variants' in res_edit.data


# ---------------------------------------------------------------------------
# 7. REST API Endpoints Tests (API_SPEC.md)
# ---------------------------------------------------------------------------
def test_api_get_products(client):
    """Test GET /api/products returns 200 and product list."""
    res = client.get('/api/products')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['count'] > 0

def test_api_get_single_product(client):
    """Test GET /api/products/1 returns product with variants."""
    res = client.get('/api/products/1')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'variants' in data['data']
    assert len(data['data']['variants']) > 0

def test_api_admin_variant_addition(app, admin_client):
    """Test POST /api/products/:id/variants adds a new variant."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    variant_id = None
    try:
        res = admin_client.post('/api/products/1/variants', json={
            'sku': f'SKU-KAN-TEST-{uid}',
            'size': 'Free Size',
            'color': 'Teal Gold',
            'purchase_price': 6500.00,
            'selling_price': 9999.00,
            'stock_quantity': 0,
            'minimum_stock': 3
        })
        assert res.status_code == 201
        data = res.get_json()
        variant_id = data['variant_id']
    finally:
        if variant_id is not None:
            with app.app_context():
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("DELETE FROM stock_movements WHERE variant_id = %s", (variant_id,))
                    cursor.execute("DELETE FROM product_variants WHERE variant_id = %s", (variant_id,))



# ---------------------------------------------------------------------------
# 8. Regression Tests: Add Variant Web Form & Optional/Required Field Handling
# ---------------------------------------------------------------------------
def test_web_add_variant_valid_success(admin_client, app):
    """Regression Test 11a: Admin adds a valid variant via POST /products/<id>/variants/add."""
    with app.app_context():
        # Ensure clean state before test
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE variant_id IN (SELECT variant_id FROM product_variants WHERE sku = 'SKU-REG-VAL-01')")
            cursor.execute("DELETE FROM product_variants WHERE sku = 'SKU-REG-VAL-01'")

    post_data = {
        'sku': 'SKU-REG-VAL-01',
        'size': 'Free Size',
        'color': 'Royal Purple',
        'purchase_price': '4500.00',
        'selling_price': '7499.00',
        'stock_quantity': '5',
        'minimum_stock': '2',
        'barcode': '8909999001'
    }
    res = admin_client.post('/products/9/variants/add', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"added successfully!" in res.data
    assert b"SKU-REG-VAL-01" in res.data

    with app.app_context():
        created_v = query_db("SELECT * FROM product_variants WHERE sku = %s", ('SKU-REG-VAL-01',), one=True)
        assert created_v is not None
        assert created_v['product_id'] == 9
        assert created_v['color'] == 'Royal Purple'
        assert float(created_v['selling_price']) == 7499.00
        assert created_v['stock_quantity'] == 5
        assert created_v['barcode'] == '8909999001'

        # Verify OPENING stock movement was created for initial opening stock
        movement = query_db("SELECT * FROM stock_movements WHERE variant_id = %s", (created_v['variant_id'],), one=True)
        assert movement is not None
        assert movement['movement_type'] == 'OPENING'
        assert movement['quantity'] == 5

        # Cleanup
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE variant_id = %s", (created_v['variant_id'],))
            cursor.execute("DELETE FROM product_variants WHERE variant_id = %s", (created_v['variant_id'],))

def test_web_add_variant_missing_optional_fields(admin_client, app):
    """Regression Test 11b: Variant creation succeeds when optional fields (barcode, purchase_price, opening stock) are omitted/blank."""
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM product_variants WHERE sku = 'SKU-REG-OPT-02'")

    post_data = {
        'sku': 'SKU-REG-OPT-02',
        'size': 'Free Size',
        'color': 'Emerald Green',
        'selling_price': '6999.00',
        'barcode': '',
        'purchase_price': '',
        'stock_quantity': ''
    }
    res = admin_client.post('/products/9/variants/add', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b"added successfully!" in res.data
    assert b"SKU-REG-OPT-02" in res.data

    with app.app_context():
        created_v = query_db("SELECT * FROM product_variants WHERE sku = %s", ('SKU-REG-OPT-02',), one=True)
        assert created_v is not None
        assert created_v['barcode'] is None
        assert float(created_v['purchase_price']) == 0.00
        assert created_v['stock_quantity'] == 0
        assert created_v['minimum_stock'] == 5

        # Zero stock creation must not create any fake stock movement
        movements = query_db("SELECT * FROM stock_movements WHERE variant_id = %s", (created_v['variant_id'],))
        assert len(movements) == 0

        # Cleanup
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM product_variants WHERE variant_id = %s", (created_v['variant_id'],))

def test_web_add_variant_missing_required_fields(admin_client):
    """Regression Test 11c: Missing required fields (sku, size, color, selling_price) fail with clear validation message."""
    # Missing SKU
    res_no_sku = admin_client.post('/products/9/variants/add', data={
        'sku': '',
        'size': 'Free Size',
        'color': 'Red',
        'selling_price': '500'
    }, follow_redirects=True)
    assert b"Variant SKU is required" in res_no_sku.data

    # Missing Size
    res_no_size = admin_client.post('/products/9/variants/add', data={
        'sku': 'SKU-TEST-NOSIZE',
        'size': '',
        'color': 'Red',
        'selling_price': '500'
    }, follow_redirects=True)
    assert b"Size is required" in res_no_size.data

    # Missing Color
    res_no_color = admin_client.post('/products/9/variants/add', data={
        'sku': 'SKU-TEST-NOCOLOR',
        'size': 'Free Size',
        'color': '',
        'selling_price': '500'
    }, follow_redirects=True)
    assert b"Color is required" in res_no_color.data

    # Missing Selling Price
    res_no_sp = admin_client.post('/products/9/variants/add', data={
        'sku': 'SKU-TEST-NOSP',
        'size': 'Free Size',
        'color': 'Red',
        'selling_price': ''
    }, follow_redirects=True)
    assert b"Selling price is required" in res_no_sp.data

def test_web_add_variant_invalid_and_blank_values(admin_client):
    """Regression Test 11d: Invalid/blank/negative values trigger clear validation errors."""
    # Negative selling price
    res_neg_sp = admin_client.post('/products/9/variants/add', data={
        'sku': 'SKU-NEG-SP-TEST',
        'size': 'Free Size',
        'color': 'Navy',
        'selling_price': '-100'
    }, follow_redirects=True)
    assert b"Selling price cannot be negative" in res_neg_sp.data

    # Negative purchase price
    res_neg_pp = admin_client.post('/products/9/variants/add', data={
        'sku': 'SKU-NEG-PP-TEST',
        'size': 'Free Size',
        'color': 'Navy',
        'purchase_price': '-50',
        'selling_price': '500'
    }, follow_redirects=True)
    assert b"Purchase price cannot be negative" in res_neg_pp.data

    # Non-existent product ID
    res_no_prod = admin_client.post('/products/99999/variants/add', data={
        'sku': 'SKU-NO-PROD-TEST',
        'size': 'Free Size',
        'color': 'Navy',
        'selling_price': '500'
    }, follow_redirects=True)
    assert b"Product not found" in res_no_prod.data

