import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import patch
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import purchase_service
from backend.services.purchase_service import ValidationError


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
# 1. Purchase List, Details & Metrics
# ---------------------------------------------------------------------------

def test_get_all_purchases(app):
    """Test fetching all purchases with supplier info and item counts."""
    with app.app_context():
        purchases = purchase_service.get_all_purchases()
        assert len(purchases) >= 3  # 3 seed purchases

        invoices = [p['invoice_number'] for p in purchases]
        assert 'PUR-KS-2026-001' in invoices
        assert 'PUR-TK-2026-042' in invoices

        p1 = next(p for p in purchases if p['invoice_number'] == 'PUR-KS-2026-001')
        assert p1['supplier_name'] == 'Sri Kanchi Silk Handloom Weavers Society'
        assert p1['item_count'] >= 1
        assert p1['total_quantity'] >= 1
        assert p1['total'] > 0


def test_purchase_summary_metrics(app):
    """Test calculation of live purchase summary metrics from the database."""
    with app.app_context():
        metrics = purchase_service.get_purchase_summary_metrics()
        assert metrics['total_purchases'] >= 3
        assert metrics['total_purchase_value'] > Decimal('0.00')
        assert 'this_month_count' in metrics
        assert 'pending_purchase_value' in metrics


def test_purchase_search_and_filters(app):
    """Test searching purchases and filtering by supplier, status, date."""
    with app.app_context():
        # Search by invoice
        res1 = purchase_service.get_all_purchases(search='PUR-KS')
        assert len(res1) >= 1
        assert any(p['invoice_number'] == 'PUR-KS-2026-001' for p in res1)

        # Search by supplier name
        res2 = purchase_service.get_all_purchases(search='Tirupur')
        assert len(res2) >= 1
        assert any(p['invoice_number'] == 'PUR-TK-2026-042' for p in res2)

        # Filter by supplier ID
        res3 = purchase_service.get_all_purchases(supplier_id=1)
        assert len(res3) >= 1
        assert all(p['supplier_id'] == 1 for p in res3)

        # Filter by payment status
        res4 = purchase_service.get_all_purchases(status='PAID')
        assert len(res4) >= 1
        assert all(p['payment_status'] == 'PAID' for p in res4)


def test_get_purchase_by_id_and_items(app):
    """Test fetching purchase header and line items by ID."""
    with app.app_context():
        purchase = purchase_service.get_purchase_by_id(1)
        assert purchase is not None
        assert purchase['invoice_number'] == 'PUR-KS-2026-001'
        assert purchase['supplier_name'] == 'Sri Kanchi Silk Handloom Weavers Society'

        items = purchase_service.get_purchase_items(1)
        assert len(items) >= 1
        first_item = items[0]
        assert 'sku' in first_item
        assert 'product_name' in first_item
        assert 'quantity' in first_item
        assert 'unit_price' in first_item
        assert 'total_price' in first_item


# ---------------------------------------------------------------------------
# 2. Purchase Creation, Calculations & Inventory Updates
# ---------------------------------------------------------------------------

def test_create_purchase_single_item_and_stock_increase(app):
    """
    Test creating a purchase with a single variant item.
    Verifies:
      - Stock increases by purchased quantity
      - Stock movement audit record created with movement_type 'PURCHASE'
      - Correct line total, subtotal, and grand total
    """
    with app.app_context():
        # Get variant initial stock (e.g. variant 1)
        variant_before = query_db("SELECT variant_id, stock_quantity FROM product_variants WHERE variant_id = 1", one=True)
        initial_stock = variant_before['stock_quantity']

        purchase_data = {
            'supplier_id': 1,
            'invoice_number': 'TEST-PUR-001',
            'purchase_date': '2026-09-25',
            'payment_status': 'PAID',
            'discount': '100.00',
            'tax': '50.00',
            'notes': 'Automated test purchase 1'
        }
        items_data = [
            {'variant_id': 1, 'quantity': 10, 'unit_price': '300.00'}
        ]

        purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id=1)
        assert purchase_id > 0

        # Verify purchase record
        purchase = purchase_service.get_purchase_by_id(purchase_id)
        assert purchase['invoice_number'] == 'TEST-PUR-001'
        assert purchase['subtotal'] == Decimal('3000.00')
        assert purchase['discount'] == Decimal('100.00')
        assert purchase['tax'] == Decimal('50.00')
        assert purchase['total'] == Decimal('2950.00')  # 3000 - 100 + 50
        assert purchase['payment_status'] == 'PAID'

        # Verify stock increment
        variant_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)
        assert variant_after['stock_quantity'] == initial_stock + 10

        # Verify stock movement record
        movement = query_db("""
            SELECT * FROM stock_movements 
            WHERE reference_type = 'PURCHASE' AND reference_id = %s AND variant_id = 1
        """, (purchase_id,), one=True)
        assert movement is not None
        assert movement['movement_type'] == 'PURCHASE'
        assert movement['quantity'] == 10
        assert movement['created_by'] == 1

        # Clean up test purchase & revert stock
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (initial_stock,))


def test_create_purchase_multiple_items(app):
    """
    Test creating a purchase with multiple distinct variant items.
    Verifies all line totals and multiple variant stock increases.
    """
    with app.app_context():
        v1_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        v2_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 2", one=True)['stock_quantity']

        purchase_data = {
            'supplier_id': 1,
            'invoice_number': 'TEST-PUR-MULTI',
            'purchase_date': '2026-09-25',
            'payment_status': 'PARTIAL',
            'discount': '500.00',
            'tax': '0.00',
            'notes': 'Multi-item test purchase'
        }
        items_data = [
            {'variant_id': 1, 'quantity': 5, 'unit_price': '1000.00'},  # 5,000
            {'variant_id': 2, 'quantity': 3, 'unit_price': '2000.00'}   # 6,000
        ]

        purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id=1)
        assert purchase_id > 0

        purchase = purchase_service.get_purchase_by_id(purchase_id)
        assert purchase['subtotal'] == Decimal('11000.00')
        assert purchase['discount'] == Decimal('500.00')
        assert purchase['total'] == Decimal('10500.00')

        items = purchase_service.get_purchase_items(purchase_id)
        assert len(items) == 2

        # Verify stock updates
        v1_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        v2_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 2", one=True)['stock_quantity']
        assert v1_after == v1_before + 5
        assert v2_after == v2_before + 3

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v1_before,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 2", (v2_before,))


# ---------------------------------------------------------------------------
# 3. Validation & Business Logic Rule Enforcement
# ---------------------------------------------------------------------------

def test_invalid_supplier_rejected(app):
    """Reject purchase when supplier does not exist."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Selected supplier does not exist"):
            purchase_service.create_purchase(
                {'supplier_id': 99999, 'invoice_number': 'INV-ERR', 'purchase_date': '2026-09-25'},
                [{'variant_id': 1, 'quantity': 5, 'unit_price': 100}],
                user_id=1
            )


def test_inactive_supplier_rejected(app):
    """Reject purchase when supplier is INACTIVE."""
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE suppliers SET status = 'INACTIVE' WHERE supplier_id = 4")

        try:
            with pytest.raises(ValidationError, match="inactive"):
                purchase_service.create_purchase(
                    {'supplier_id': 4, 'invoice_number': 'INV-INACTIVE-SUP', 'purchase_date': '2026-09-25'},
                    [{'variant_id': 1, 'quantity': 5, 'unit_price': 100}],
                    user_id=1
                )
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("UPDATE suppliers SET status = 'ACTIVE' WHERE supplier_id = 4")


def test_invalid_variant_rejected(app):
    """Reject purchase when variant does not exist."""
    with app.app_context():
        with pytest.raises(ValidationError, match="does not exist"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-NO-VAR', 'purchase_date': '2026-09-25'},
                [{'variant_id': 99999, 'quantity': 5, 'unit_price': 100}],
                user_id=1
            )


def test_inactive_variant_rejected(app):
    """Reject purchase when variant is marked INACTIVE."""
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("UPDATE product_variants SET status = 'INACTIVE' WHERE variant_id = 6")

        try:
            with pytest.raises(ValidationError, match="inactive"):
                purchase_service.create_purchase(
                    {'supplier_id': 1, 'invoice_number': 'INV-INACTIVE-VAR', 'purchase_date': '2026-09-25'},
                    [{'variant_id': 6, 'quantity': 5, 'unit_price': 100}],
                    user_id=1
                )
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("UPDATE product_variants SET status = 'ACTIVE' WHERE variant_id = 6")


def test_zero_quantity_rejected(app):
    """Reject purchase with quantity = 0."""
    with app.app_context():
        with pytest.raises(ValidationError, match="greater than zero"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-ZERO-QTY', 'purchase_date': '2026-09-25'},
                [{'variant_id': 1, 'quantity': 0, 'unit_price': 100}],
                user_id=1
            )


def test_negative_quantity_rejected(app):
    """Reject purchase with negative quantity."""
    with app.app_context():
        with pytest.raises(ValidationError, match="greater than zero"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-NEG-QTY', 'purchase_date': '2026-09-25'},
                [{'variant_id': 1, 'quantity': -5, 'unit_price': 100}],
                user_id=1
            )


def test_negative_price_rejected(app):
    """Reject purchase with negative unit price."""
    with app.app_context():
        with pytest.raises(ValidationError, match="cannot be negative"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-NEG-PRICE', 'purchase_date': '2026-09-25'},
                [{'variant_id': 1, 'quantity': 5, 'unit_price': -100}],
                user_id=1
            )


def test_negative_discount_rejected(app):
    """Reject purchase with negative discount."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Discount cannot be negative"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-NEG-DISC', 'purchase_date': '2026-09-25', 'discount': -50},
                [{'variant_id': 1, 'quantity': 5, 'unit_price': 100}],
                user_id=1
            )


def test_negative_tax_rejected(app):
    """Reject purchase with negative tax."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Tax cannot be negative"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-NEG-TAX', 'purchase_date': '2026-09-25', 'tax': -20},
                [{'variant_id': 1, 'quantity': 5, 'unit_price': 100}],
                user_id=1
            )


def test_grand_total_negative_rejected(app):
    """Reject purchase when discount exceeds subtotal resulting in negative total."""
    with app.app_context():
        with pytest.raises(ValidationError, match="cannot be negative"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-EXCESS-DISC', 'purchase_date': '2026-09-25', 'discount': 1000},
                [{'variant_id': 1, 'quantity': 2, 'unit_price': 100}],  # subtotal = 200, discount = 1000 -> -800
                user_id=1
            )


def test_duplicate_variant_in_same_purchase_rejected(app):
    """Reject purchase when same variant ID is included more than once."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Duplicate variant detected"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-DUP-VAR', 'purchase_date': '2026-09-25'},
                [
                    {'variant_id': 1, 'quantity': 5, 'unit_price': 100},
                    {'variant_id': 1, 'quantity': 3, 'unit_price': 100}
                ],
                user_id=1
            )


def test_empty_items_rejected(app):
    """Reject purchase with no items."""
    with app.app_context():
        with pytest.raises(ValidationError, match="at least one product variant"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': 'INV-EMPTY', 'purchase_date': '2026-09-25'},
                [],
                user_id=1
            )


def test_missing_invoice_number_rejected(app):
    """Reject purchase without invoice number."""
    with app.app_context():
        with pytest.raises(ValidationError, match="invoice / reference number is required"):
            purchase_service.create_purchase(
                {'supplier_id': 1, 'invoice_number': '', 'purchase_date': '2026-09-25'},
                [{'variant_id': 1, 'quantity': 5, 'unit_price': 100}],
                user_id=1
            )


# ---------------------------------------------------------------------------
# 4. Atomic Transaction & Rollback Safety Tests
# ---------------------------------------------------------------------------

def test_transaction_rollback_when_stock_update_fails(app):
    """
    Test atomicity: If stock update fails midway, everything rolls back.
    No purchase header, no purchase items, no stock movement, and stock untouched.
    """
    with app.app_context():
        v1_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        invoice_num = 'INV-ROLLBACK-TEST-1'

        purchase_data = {
            'supplier_id': 1,
            'invoice_number': invoice_num,
            'purchase_date': '2026-09-25'
        }
        items_data = [
            {'variant_id': 1, 'quantity': 10, 'unit_price': '200.00'}
        ]

        # Simulate failure during execution
        with patch('backend.services.purchase_service.get_db_connection') as mock_conn:
            import mysql.connector
            from backend.utils.database import get_db_connection as real_get_db_connection
            real_conn = real_get_db_connection()
            mock_conn.return_value = real_conn

            # Cause cursor to raise error on stock update
            real_cursor = real_conn.cursor(dictionary=True)
            original_execute = real_cursor.execute

            def side_effect_execute(sql, params=None):
                if 'UPDATE product_variants' in sql:
                    raise Exception("SIMULATED DATABASE DISK / LOCK ERROR ON STOCK UPDATE")
                return original_execute(sql, params)

            real_cursor.execute = side_effect_execute
            real_conn.cursor = lambda *args, **kwargs: real_cursor

            with pytest.raises(ValidationError, match="Failed to save purchase"):
                purchase_service.create_purchase(purchase_data, items_data, user_id=1)

        # Verify nothing was saved in database
        saved_p = query_db("SELECT * FROM purchases WHERE invoice_number = %s", (invoice_num,), one=True)
        assert saved_p is None

        # Verify stock remains unchanged
        v1_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v1_after == v1_before

        # Verify no orphaned stock movements
        movements = query_db("SELECT * FROM stock_movements WHERE notes LIKE %s", (f"%{invoice_num}%",))
        assert len(movements) == 0


def test_supplier_purchase_history_updated_after_purchase(app):
    """
    Test that creating a purchase automatically reflects in the supplier's
    purchase count and cumulative purchase spend.
    """
    with app.app_context():
        sup_before = query_db("""
            SELECT COUNT(p.purchase_id) as p_count, COALESCE(SUM(p.total), 0) as p_total
            FROM purchases p WHERE p.supplier_id = 2
        """, one=True)
        count_before = sup_before['p_count']
        total_before = sup_before['p_total']

        purchase_data = {
            'supplier_id': 2,
            'invoice_number': 'TEST-SUP-HIST-01',
            'purchase_date': '2026-09-25',
            'payment_status': 'PAID',
            'discount': '0.00',
            'tax': '0.00'
        }
        items_data = [
            {'variant_id': 1, 'quantity': 2, 'unit_price': '500.00'}  # Total = 1000
        ]

        v1_stock = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        purchase_id = purchase_service.create_purchase(purchase_data, items_data, user_id=1)

        # Verify supplier aggregates
        sup_after = query_db("""
            SELECT COUNT(p.purchase_id) as p_count, COALESCE(SUM(p.total), 0) as p_total
            FROM purchases p WHERE p.supplier_id = 2
        """, one=True)
        assert sup_after['p_count'] == count_before + 1
        assert sup_after['p_total'] == total_before + Decimal('1000.00')

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v1_stock,))


# ---------------------------------------------------------------------------
# 5. Web Routes & RBAC Authorization Tests
# ---------------------------------------------------------------------------

def test_web_purchases_list_unauthenticated(client):
    """Unauthenticated users must be redirected to login page."""
    response = client.get('/purchases')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')


def test_web_purchases_list_staff_access(staff_client):
    """Staff can view the purchases list page."""
    response = staff_client.get('/purchases')
    assert response.status_code == 200
    assert b'Purchases' in response.data
    assert b'PUR-KS-2026-001' in response.data


def test_web_purchases_view_page(staff_client):
    """Staff can view purchase detail / bill page."""
    response = staff_client.get('/purchases/1')
    assert response.status_code == 200
    assert b'PUR-KS-2026-001' in response.data
    assert b'Sri Kanchi Silk' in response.data
    assert b'Inventory Impact' in response.data


def test_web_purchases_new_staff_denied(staff_client):
    """Staff cannot access new purchase creation form (Admin only)."""
    response = staff_client.get('/purchases/new', follow_redirects=True)
    assert b'Administrator access required' in response.data


def test_web_purchases_admin_new_page(admin_client):
    """Admin can access new purchase creation form."""
    response = admin_client.get('/purchases/new')
    assert response.status_code == 200
    assert b'New Purchase' in response.data
    assert b'Supplier' in response.data


def test_web_purchases_admin_create_success(admin_client, app):
    """Admin can submit new purchase form via Web POST and get redirected to view."""
    with app.app_context():
        v1_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    post_data = {
        'supplier_id': '1',
        'invoice_number': 'WEB-TEST-INV-99',
        'purchase_date': '2026-09-25',
        'payment_status': 'PAID',
        'discount': '50.00',
        'tax': '0.00',
        'notes': 'Web form purchase test',
        'variant_id[]': ['1'],
        'quantity[]': ['4'],
        'unit_price[]': ['250.00']
    }

    response = admin_client.post('/purchases/new', data=post_data, follow_redirects=True)
    assert response.status_code == 200
    assert b'WEB-TEST-INV-99' in response.data
    assert b'created successfully' in response.data

    with app.app_context():
        v1_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v1_after == v1_before + 4

        # Clean up
        p = query_db("SELECT purchase_id FROM purchases WHERE invoice_number = 'WEB-TEST-INV-99'", one=True)
        if p:
            pid = p['purchase_id']
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (pid,))
                cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (pid,))
                cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (pid,))
                cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v1_before,))


# ---------------------------------------------------------------------------
# 6. REST API Tests
# ---------------------------------------------------------------------------

def test_api_purchases_list(admin_client):
    """GET /api/purchases returns JSON list of purchases."""
    response = admin_client.get('/api/purchases')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['count'] >= 3
    assert len(data['purchases']) >= 3


def test_api_purchase_detail(admin_client):
    """GET /api/purchases/<id> returns purchase with items array."""
    response = admin_client.get('/api/purchases/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['purchase']['invoice_number'] == 'PUR-KS-2026-001'
    assert len(data['purchase']['items']) >= 1


def test_api_purchase_not_found(admin_client):
    """GET /api/purchases/99999 returns 404."""
    response = admin_client.get('/api/purchases/99999')
    assert response.status_code == 404
    data = response.get_json()
    assert data['status'] == 'error'


def test_api_purchase_create_admin_success(admin_client, app):
    """POST /api/purchases creates purchase and increments stock via REST API."""
    with app.app_context():
        v1_before = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']

    payload = {
        'supplier_id': 1,
        'invoice_number': 'API-INV-TEST-001',
        'purchase_date': '2026-09-25',
        'payment_status': 'PAID',
        'discount': 100.0,
        'tax': 20.0,
        'notes': 'Created via REST API test',
        'items': [
            {'variant_id': 1, 'quantity': 6, 'unit_price': 500.0}
        ]
    }

    response = admin_client.post('/api/purchases', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['invoice_number'] == 'API-INV-TEST-001'
    purchase_id = data['purchase_id']

    with app.app_context():
        v1_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = 1", one=True)['stock_quantity']
        assert v1_after == v1_before + 6

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'PURCHASE' AND reference_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchase_items WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("DELETE FROM purchases WHERE purchase_id = %s", (purchase_id,))
            cursor.execute("UPDATE product_variants SET stock_quantity = %s WHERE variant_id = 1", (v1_before,))


def test_api_purchase_create_staff_forbidden(staff_client):
    """Staff cannot create purchases via POST /api/purchases (403)."""
    payload = {
        'supplier_id': 1,
        'invoice_number': 'STAFF-DENIED-INV',
        'purchase_date': '2026-09-25',
        'items': [{'variant_id': 1, 'quantity': 2, 'unit_price': 100.0}]
    }
    response = staff_client.post('/api/purchases', json=payload)
    assert response.status_code == 403


def test_api_purchase_create_validation_error(admin_client):
    """POST /api/purchases with invalid payload returns 400 error."""
    payload = {
        'supplier_id': 1,
        'invoice_number': 'ERR-INV',
        'purchase_date': '2026-09-25',
        'items': [{'variant_id': 1, 'quantity': -5, 'unit_price': 100.0}]
    }
    response = admin_client.post('/api/purchases', json=payload)
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'greater than zero' in data['message']
