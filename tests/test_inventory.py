import pytest
from decimal import Decimal
from unittest.mock import patch
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import inventory_service
from backend.services.inventory_service import ValidationError


@pytest.fixture
def app():
    """Create test app instance."""
    app = create_app('testing')
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE product_variants SET stock_quantity = 12 WHERE variant_id = 1 AND stock_quantity < 5")
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
# 1. Inventory Listing, Stock Status & Metrics Tests
# ---------------------------------------------------------------------------

def test_inventory_list(app):
    """Test fetching full inventory list with computed stock status."""
    with app.app_context():
        items = inventory_service.get_inventory()
        assert len(items) >= 20  # Seed variants

        first = items[0]
        assert 'sku' in first
        assert 'product_name' in first
        assert 'stock_quantity' in first
        assert 'minimum_stock' in first
        assert 'stock_status' in first
        assert first['stock_status'] in ('IN_STOCK', 'LOW_STOCK', 'OUT_OF_STOCK')


def test_inventory_summary_metrics(app):
    """Test inventory summary metrics calculation."""
    with app.app_context():
        metrics = inventory_service.get_inventory_summary_metrics()
        assert metrics['total_variants'] >= 20
        assert metrics['total_units'] > 0
        assert metrics['in_stock_count'] >= 0
        assert metrics['low_stock_count'] >= 0
        assert metrics['out_of_stock_count'] >= 0
        assert metrics['total_cost_value'] > Decimal('0.00')
        assert metrics['total_retail_value'] > Decimal('0.00')


def test_inventory_product_search(app):
    """Test searching inventory by garment product name."""
    with app.app_context():
        items = inventory_service.get_inventory(search='Kanchipuram')
        assert len(items) >= 1
        assert all('Kanchipuram' in item['product_name'] or 'Kanchipuram' in item.get('brand', '') for item in items)


def test_inventory_sku_search(app):
    """Test searching inventory by variant SKU."""
    with app.app_context():
        items = inventory_service.get_inventory(search='SKU-KAN-RED')
        assert len(items) == 1
        assert items[0]['sku'] == 'SKU-KAN-RED'


def test_inventory_barcode_search(app):
    """Test searching inventory by barcode."""
    with app.app_context():
        v = query_db("SELECT barcode FROM product_variants WHERE barcode IS NOT NULL LIMIT 1", one=True)
        if v and v['barcode']:
            items = inventory_service.get_inventory(search=v['barcode'])
            assert len(items) >= 1
            assert any(item['barcode'] == v['barcode'] for item in items)


def test_inventory_category_filter(app):
    """Test filtering inventory by category ID."""
    with app.app_context():
        items = inventory_service.get_inventory(category_id=1)
        assert len(items) >= 1
        assert all(item['category_id'] == 1 for item in items)


def test_inventory_in_stock_filter(app):
    """Test filtering inventory by IN_STOCK status."""
    with app.app_context():
        items = inventory_service.get_inventory(stock_status='IN_STOCK')
        assert len(items) >= 1
        assert all(item['stock_quantity'] > item['minimum_stock'] for item in items)


def test_inventory_low_stock_filter(app):
    """Test filtering inventory by LOW_STOCK status."""
    with app.app_context():
        items = inventory_service.get_inventory(stock_status='LOW_STOCK')
        assert all(item['stock_quantity'] > 0 and item['stock_quantity'] <= item['minimum_stock'] for item in items)


def test_inventory_out_of_stock_filter(app):
    """Test filtering inventory by OUT_OF_STOCK status."""
    with app.app_context():
        items = inventory_service.get_inventory(stock_status='OUT_OF_STOCK')
        assert all(item['stock_quantity'] == 0 for item in items)


def test_get_low_stock_items(app):
    """Test get_low_stock_items service method."""
    with app.app_context():
        items = inventory_service.get_low_stock_items()
        assert isinstance(items, list)
        for it in items:
            assert it['stock_quantity'] > 0
            assert it['stock_quantity'] <= it['minimum_stock']
            assert it['stock_status'] == 'LOW_STOCK'
            assert 'units_needed' in it


def test_get_out_of_stock_items(app):
    """Test get_out_of_stock_items service method."""
    with app.app_context():
        items = inventory_service.get_out_of_stock_items()
        assert isinstance(items, list)
        for it in items:
            assert it['stock_quantity'] == 0
            assert it['stock_status'] == 'OUT_OF_STOCK'


# ---------------------------------------------------------------------------
# 2. Stock Movements Audit Ledger Tests
# ---------------------------------------------------------------------------

def test_get_stock_movements_list(app):
    """Test fetching chronological stock movements with join details."""
    with app.app_context():
        movements = inventory_service.get_stock_movements()
        assert len(movements) >= 5  # Seed movements

        first = movements[0]
        assert 'movement_id' in first
        assert 'variant_id' in first
        assert 'movement_type' in first
        assert 'quantity' in first
        assert 'created_by_name' in first
        assert 'product_name' in first
        assert 'sku' in first


def test_stock_movements_filter_by_type(app):
    """Test filtering movements by movement_type (e.g. PURCHASE, SALE, OPENING)."""
    with app.app_context():
        purchases = inventory_service.get_stock_movements(movement_type='PURCHASE')
        assert all(m['movement_type'] == 'PURCHASE' for m in purchases)

        sales = inventory_service.get_stock_movements(movement_type='SALE')
        assert all(m['movement_type'] == 'SALE' for m in sales)


def test_stock_movements_filter_by_date(app):
    """Test filtering movements by date range."""
    with app.app_context():
        movements = inventory_service.get_stock_movements(date_from='2026-09-01', date_to='2026-09-30')
        assert len(movements) >= 1


# ---------------------------------------------------------------------------
# 3. Manual Stock Adjustment & Damaged Stock Tests
# ---------------------------------------------------------------------------

def test_admin_adjustment_increase(app):
    """Test admin stock adjustment increase (+5 units)."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        res = inventory_service.adjust_stock(
            variant_id=1,
            adjustment_type='INCREASE',
            quantity=5,
            reason='Physical stock audit surplus found on shelf',
            user_id=1
        )

        assert res['previous_stock'] == v_before
        assert res['delta'] == 5
        assert res['new_stock'] == v_before + 5

        # Check database updated
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before + 5

        # Check movement audit log
        movement = query_db("""
            SELECT * FROM stock_movements 
            WHERE variant_id = 1 AND movement_type = 'ADJUSTMENT' AND notes LIKE '%Physical stock audit%'
            ORDER BY movement_id DESC LIMIT 1
        """, one=True)
        assert movement is not None
        assert movement['quantity'] == 5
        assert movement['created_by'] == 1

        # Revert
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE movement_id = %s", (movement['movement_id'],))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_admin_adjustment_decrease(app):
    """Test admin stock adjustment decrease (-2 units)."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        res = inventory_service.adjust_stock(
            variant_id=1,
            adjustment_type='DECREASE',
            quantity=2,
            reason='Audit count reconciliation shrinkage',
            user_id=1
        )

        assert res['delta'] == -2
        assert res['new_stock'] == v_before - 2

        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before - 2

        movement = query_db("""
            SELECT * FROM stock_movements 
            WHERE variant_id = 1 AND movement_type = 'ADJUSTMENT' AND notes LIKE '%reconciliation shrinkage%'
            ORDER BY movement_id DESC LIMIT 1
        """, one=True)
        assert movement is not None
        assert movement['quantity'] == -2

        # Revert
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE movement_id = %s", (movement['movement_id'],))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_adjustment_negative_stock_prevented(app):
    """Reject adjustment decrease that exceeds current stock."""
    with app.app_context():
        v_current = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        with pytest.raises(ValidationError, match="Cannot decrease stock"):
            inventory_service.adjust_stock(
                variant_id=1,
                adjustment_type='DECREASE',
                quantity=v_current + 100,
                reason='Impossible decrease test',
                user_id=1
            )

        # Confirm stock unchanged
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_current


def test_adjustment_zero_quantity_rejected(app):
    """Reject adjustment with quantity = 0."""
    with app.app_context():
        with pytest.raises(ValidationError, match="greater than zero"):
            inventory_service.adjust_stock(variant_id=1, adjustment_type='INCREASE', quantity=0, reason='Zero test', user_id=1)


def test_adjustment_negative_quantity_rejected(app):
    """Reject adjustment with negative quantity."""
    with app.app_context():
        with pytest.raises(ValidationError, match="greater than zero"):
            inventory_service.adjust_stock(variant_id=1, adjustment_type='INCREASE', quantity=-3, reason='Neg test', user_id=1)


def test_adjustment_invalid_variant_rejected(app):
    """Reject adjustment for non-existent variant ID."""
    with app.app_context():
        with pytest.raises(ValidationError, match="does not exist"):
            inventory_service.adjust_stock(variant_id=99999, adjustment_type='INCREASE', quantity=5, reason='Invalid var test', user_id=1)


def test_adjustment_inactive_variant_rejected(app):
    """Reject adjustment for an INACTIVE variant."""
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE product_variants SET status = 'INACTIVE' WHERE variant_id = 6")

        try:
            with pytest.raises(ValidationError, match="inactive"):
                inventory_service.adjust_stock(variant_id=6, adjustment_type='INCREASE', quantity=2, reason='Inactive test', user_id=1)
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("UPDATE product_variants SET status = 'ACTIVE' WHERE variant_id = 6")


def test_adjustment_missing_reason_rejected(app):
    """Reject adjustment without mandatory reason."""
    with app.app_context():
        with pytest.raises(ValidationError, match="reason / remark is required"):
            inventory_service.adjust_stock(variant_id=1, adjustment_type='INCREASE', quantity=2, reason='', user_id=1)


def test_damaged_stock_decrease(app):
    """Test writing off damaged stock with movement_type 'DAMAGE'."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        res = inventory_service.record_damaged_stock(
            variant_id=1,
            quantity=2,
            reason='Rainwater leakage water stains on border',
            user_id=1
        )

        assert res['previous_stock'] == v_before
        assert res['damaged_quantity'] == 2
        assert res['new_stock'] == v_before - 2
        assert res['movement_type'] == 'DAMAGE'

        # Check movement audit log
        movement = query_db("""
            SELECT * FROM stock_movements 
            WHERE variant_id = 1 AND movement_type = 'DAMAGE' AND notes LIKE '%Rainwater leakage%'
            ORDER BY movement_id DESC LIMIT 1
        """, one=True)
        assert movement is not None
        assert movement['quantity'] == -2

        # Revert
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE movement_id = %s", (movement['movement_id'],))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_damaged_stock_exceeding_available_rejected(app):
    """Reject writing off more damaged units than available stock."""
    with app.app_context():
        v_current = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        with pytest.raises(ValidationError, match="Cannot write off"):
            inventory_service.record_damaged_stock(
                variant_id=1,
                quantity=v_current + 50,
                reason='Excessive damage write-off test',
                user_id=1
            )


def test_damaged_stock_missing_reason_rejected(app):
    """Reject recording damaged stock without a reason."""
    with app.app_context():
        with pytest.raises(ValidationError, match="reason / inspection note is required"):
            inventory_service.record_damaged_stock(variant_id=1, quantity=1, reason='', user_id=1)


# ---------------------------------------------------------------------------
# 4. Atomic Transaction & Rollback Safety Tests
# ---------------------------------------------------------------------------

def test_transaction_rollback_when_stock_update_fails(app):
    """Test that if stock update fails, no stock movement is created."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        with patch('backend.services.inventory_service.get_db_connection') as mock_conn:
            from backend.utils.database import get_db_connection as real_get_db_connection
            real_conn = real_get_db_connection()
            mock_conn.return_value = real_conn

            real_cursor = real_conn.cursor(dictionary=True)
            original_execute = real_cursor.execute

            def side_effect_execute(sql, params=None):
                if 'UPDATE product_variants' in sql:
                    raise Exception("SIMULATED DATABASE DEADLOCK ERROR")
                return original_execute(sql, params)

            real_cursor.execute = side_effect_execute
            real_conn.cursor = lambda dictionary=True: real_cursor

            with pytest.raises(ValidationError, match="Stock adjustment failed"):
                inventory_service.adjust_stock(variant_id=1, adjustment_type='INCREASE', quantity=10, reason='Deadlock test', user_id=1)

        # Verify stock untouched
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before

        # Verify no orphaned movements
        orphan = query_db("SELECT * FROM stock_movements WHERE notes LIKE '%Deadlock test%'", one=True)
        assert orphan is None


def test_transaction_rollback_when_movement_insert_fails(app):
    """Test that if movement insertion fails, stock quantity update is rolled back."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        with patch('backend.services.inventory_service.get_db_connection') as mock_conn:
            from backend.utils.database import get_db_connection as real_get_db_connection
            real_conn = real_get_db_connection()
            mock_conn.return_value = real_conn

            real_cursor = real_conn.cursor(dictionary=True)
            original_execute = real_cursor.execute

            def side_effect_execute(sql, params=None):
                if 'INSERT INTO stock_movements' in sql:
                    raise Exception("SIMULATED DISK FULL ERROR ON AUDIT INSERT")
                return original_execute(sql, params)

            real_cursor.execute = side_effect_execute
            real_conn.cursor = lambda dictionary=True: real_cursor

            with pytest.raises(ValidationError, match="Stock adjustment failed"):
                inventory_service.adjust_stock(variant_id=1, adjustment_type='INCREASE', quantity=10, reason='Audit fail test', user_id=1)

        # Verify stock untouched
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before


# ---------------------------------------------------------------------------
# 5. Web Routes & RBAC Authorization Tests
# ---------------------------------------------------------------------------

def test_web_inventory_unauthenticated_redirects(client):
    """Unauthenticated access to /inventory must redirect to login."""
    response = client.get('/inventory')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')


def test_web_inventory_staff_can_view(staff_client):
    """Staff can view inventory and alert pages."""
    res1 = staff_client.get('/inventory')
    assert res1.status_code == 200
    assert b'Inventory &amp; Stock' in res1.data or b'Inventory' in res1.data

    res2 = staff_client.get('/inventory/low-stock')
    assert res2.status_code == 200
    assert b'Low Stock' in res2.data

    res3 = staff_client.get('/inventory/out-of-stock')
    assert res3.status_code == 200
    assert b'Out of Stock' in res3.data

    res4 = staff_client.get('/inventory/movements')
    assert res4.status_code == 200
    assert b'Movement Audit Log' in res4.data


def test_web_inventory_adjustment_staff_denied(staff_client):
    """Staff cannot access /inventory/adjustment (Admin only)."""
    response = staff_client.get('/inventory/adjustment', follow_redirects=True)
    assert b'Administrator access required' in response.data


def test_web_inventory_adjustment_admin_post_success(admin_client, app):
    """Admin can submit stock adjustment via web form."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    post_data = {
        'action_type': 'ADJUSTMENT',
        'variant_id': '1',
        'adjustment_type': 'INCREASE',
        'quantity': '3',
        'reason': 'Web form test adjustment'
    }
    response = admin_client.post('/inventory/adjustment', data=post_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Stock adjusted for' in response.data

    with app.app_context():
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before + 3

        # Revert
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE notes LIKE '%Web form test adjustment%'")
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_web_inventory_damage_admin_post_success(admin_client, app):
    """Admin can submit damaged stock write-off via web form."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    post_data = {
        'action_type': 'DAMAGE',
        'variant_id': '1',
        'adjustment_type': 'DECREASE',
        'quantity': '1',
        'reason': 'Web form damaged stock write-off test'
    }
    response = admin_client.post('/inventory/adjustment', data=post_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Damaged stock recorded' in response.data

    with app.app_context():
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before - 1

        # Revert
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE notes LIKE '%Web form damaged stock write-off test%'")
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


# ---------------------------------------------------------------------------
# 6. REST API Endpoints Tests
# ---------------------------------------------------------------------------

def test_api_inventory_list(staff_client):
    """GET /api/inventory returns JSON list with count & computed stock_status."""
    response = staff_client.get('/api/inventory')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['count'] >= 20
    assert len(data['inventory']) >= 20


def test_api_inventory_low_stock(staff_client):
    """GET /api/inventory/low-stock returns JSON list of low stock variants."""
    response = staff_client.get('/api/inventory/low-stock')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'low_stock_items' in data


def test_api_inventory_movements(staff_client):
    """GET /api/inventory/movements returns JSON movements array."""
    response = staff_client.get('/api/inventory/movements')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'movements' in data
    assert len(data['movements']) >= 5


def test_api_adjustment_admin_success(admin_client, app):
    """POST /api/inventory/adjustment allows Admin to adjust stock."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    payload = {
        'variant_id': 1,
        'adjustment_type': 'INCREASE',
        'quantity': 4,
        'reason': 'API adjustment test'
    }
    response = admin_client.post('/api/inventory/adjustment', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['new_stock'] == v_before + 4

    with app.app_context():
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before + 4

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE notes LIKE '%API adjustment test%'")
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_api_adjustment_damage_admin_success(admin_client, app):
    """POST /api/inventory/adjustment allows Admin to write off damaged stock."""
    with app.app_context():
        v_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    payload = {
        'variant_id': 1,
        'adjustment_type': 'DAMAGE',
        'quantity': 2,
        'reason': 'API damage test'
    }
    response = admin_client.post('/api/inventory/adjustment', json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['movement_type'] == 'DAMAGE'
    assert data['data']['new_stock'] == v_before - 2

    with app.app_context():
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v_after == v_before - 2

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE notes LIKE '%API damage test%'")
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v_before,))


def test_api_adjustment_staff_forbidden(staff_client):
    """POST /api/inventory/adjustment forbids Staff access (403)."""
    payload = {
        'variant_id': 1,
        'adjustment_type': 'INCREASE',
        'quantity': 2,
        'reason': 'Staff unauthorized adjustment'
    }
    response = staff_client.post('/api/inventory/adjustment', json=payload)
    assert response.status_code == 403


def test_api_adjustment_validation_error(admin_client):
    """POST /api/inventory/adjustment with invalid quantity returns 400 error."""
    payload = {
        'variant_id': 1,
        'adjustment_type': 'INCREASE',
        'quantity': -5,
        'reason': 'Negative test'
    }
    response = admin_client.post('/api/inventory/adjustment', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'greater than zero' in data['message']


def test_purchase_stock_integrity_preserved(admin_client, app):
    """
    Verify that creating a purchase still correctly updates stock,
    and the new stock quantity immediately reflects in the inventory service and metrics.
    """
    from backend.services import purchase_service
    with app.app_context():
        v1_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

        purchase_data = {
            'supplier_id': 1,
            'invoice_number': 'TEST-INV-INTEG-01',
            'purchase_date': '2026-09-25',
            'payment_status': 'PAID',
            'discount': '0.00',
            'tax': '0.00'
        }
        items_data = [
            {'variant_id': 1, 'quantity': 8, 'unit_price': '600.00'}
        ]

        purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id=1)

        # Check inventory listing reflects the updated stock
        inventory_items = inventory_service.get_inventory(search='SKU-KAN-RED')
        assert len(inventory_items) >= 1
        assert inventory_items[0]['stock_quantity'] == v1_before + 8

        # Check stock movements contains the PURCHASE movement
        movements = inventory_service.get_stock_movements(variant_id=1, movement_type='PURCHASE')
        assert any(m['reference_id'] == purchase_id for m in movements)

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v1_before,))
