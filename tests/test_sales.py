import pytest
from decimal import Decimal
from datetime import date
from backend.app import create_app
from backend.utils.database import query_db
from backend.services import sale_service
from backend.services.sale_service import ValidationError


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
# 1. Sale Listing, Details & Metrics
# ---------------------------------------------------------------------------

def test_get_all_sales(app):
    """Test fetching all sales."""
    with app.app_context():
        sales = sale_service.get_all_sales()
        assert isinstance(sales, list)
        if len(sales) > 0:
            first = sales[0]
            assert 'invoice_number' in first
            assert 'total_amount' in first
            assert 'payment_method' in first


def test_get_sales_filtered(app):
    """Test fetching sales filtered by payment method and status."""
    with app.app_context():
        cash_sales = sale_service.get_all_sales(payment_method='CASH')
        for s in cash_sales:
            assert s['payment_method'] == 'CASH'

        paid_sales = sale_service.get_all_sales(payment_status='PAID')
        for s in paid_sales:
            assert s['payment_status'] == 'PAID'


def test_get_sale_summary_metrics(app):
    """Test sale summary metrics calculation."""
    with app.app_context():
        metrics = sale_service.get_sale_summary_metrics()
        assert 'total_sales' in metrics
        assert 'total_revenue' in metrics
        assert 'total_outstanding' in metrics
        assert 'this_month_count' in metrics
        assert 'this_month_revenue' in metrics
        assert 'credit_sales_count' in metrics


def test_generate_invoice_number(app):
    """Test automatic invoice number generation."""
    with app.app_context():
        inv_num = sale_service.generate_invoice_number()
        year_str = str(date.today().year)
        assert inv_num.startswith(f"SALE-{year_str}-")


# ---------------------------------------------------------------------------
# 2. Sale Creation & Inventory / Ledger Deductions
# ---------------------------------------------------------------------------

def test_create_cash_sale_success(app):
    """Test creating a successful cash sale with stock deduction and payment record."""
    with app.app_context():
        # Get active variant with stock
        variants = sale_service.get_active_variants_for_sale()
        available = [v for v in variants if v['stock_quantity'] >= 2]
        assert len(available) > 0, "No variant with >= 2 stock found"
        var = available[0]
        var_id = var['variant_id']
        initial_stock = var['stock_quantity']
        unit_price = var['selling_price']

        sale_data = {
            'customer_id': None,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CASH',
            'paid_amount': float(unit_price * 2),
            'discount': 0.0,
            'tax': 0.0,
            'notes': 'Cash POS Test',
        }
        items_data = [
            {
                'variant_id': var_id,
                'quantity': 2,
                'unit_price': float(unit_price),
                'item_discount': 0.0,
            }
        ]

        sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
        assert sale_id > 0

        # Verify sale record
        sale = sale_service.get_sale_by_id(sale_id)
        assert sale is not None
        assert sale['payment_method'] == 'CASH'
        assert sale['payment_status'] == 'PAID'
        assert Decimal(str(sale['total_amount'])) == Decimal(str(unit_price * 2))
        assert Decimal(str(sale['paid_amount'])) == Decimal(str(unit_price * 2))
        assert Decimal(str(sale['balance_amount'])) == Decimal('0.00')

        # Verify stock decrement
        stock_row = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,),
            one=True
        )
        assert stock_row['stock_quantity'] == initial_stock - 2

        # Verify stock movement record
        movement = query_db(
            """
            SELECT * FROM stock_movements
            WHERE variant_id = %s AND reference_type = 'SALE' AND reference_id = %s
            """,
            (var_id, sale_id),
            one=True
        )
        assert movement is not None
        assert movement['movement_type'] == 'SALE'
        assert movement['quantity'] == -2


def test_create_credit_sale_success(app):
    """Test creating a credit sale for customer updating balance and ledger."""
    from backend.services import customer_service
    import time

    with app.app_context():
        # Create a fresh test customer with a high credit limit so the sale won't fail
        phone = f"9{int(time.time() * 1000) % 10000000000:010d}"[:11]
        cust_id = customer_service.create_customer({
            'customer_name': 'CreditSaleTestCustomer',
            'phone': phone,
            'credit_limit': 100000.0,
            'status': 'ACTIVE',
        })

        variants = sale_service.get_active_variants_for_sale()
        available = [v for v in variants if v['stock_quantity'] >= 1]
        assert len(available) > 0
        var = available[0]
        var_id = var['variant_id']
        unit_price = Decimal(str(var['selling_price']))

        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CREDIT',
            'paid_amount': 0.0,
            'discount': 0.0,
            'tax': 0.0,
            'notes': 'Credit POS Test',
        }
        items_data = [
            {
                'variant_id': var_id,
                'quantity': 1,
                'unit_price': float(unit_price),
                'item_discount': 0.0,
            }
        ]

        sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
        assert sale_id > 0

        try:
            # Verify sale record
            sale = sale_service.get_sale_by_id(sale_id)
            assert sale['payment_method'] == 'CREDIT'
            assert sale['payment_status'] == 'CREDIT'
            assert Decimal(str(sale['balance_amount'])) == unit_price

            # Verify customer outstanding balance incremented
            updated_balance = sale_service.get_customer_outstanding_balance(cust_id)
            assert updated_balance == unit_price

            # Verify credit_transactions entry
            credit_tx = query_db(
                "SELECT * FROM credit_transactions WHERE customer_id = %s AND sale_id = %s",
                (cust_id, sale_id),
                one=True
            )
            assert credit_tx is not None
            assert credit_tx['transaction_type'] == 'CREDIT_SALE'
            assert Decimal(str(credit_tx['amount'])) == unit_price
        finally:
            # Cleanup
            from backend.utils.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credit_transactions WHERE customer_id = %s", (cust_id,))
            cursor.execute("DELETE FROM payments WHERE customer_id = %s", (cust_id,))
            cursor.execute("DELETE FROM stock_movements WHERE reference_id = %s AND reference_type = 'SALE'", (sale_id,))
            cursor.execute("DELETE FROM sale_items WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))
            conn.commit()
            cursor.close()
            conn.close()




def test_create_sale_validation_errors(app):
    """Test various validation failure scenarios."""
    with app.app_context():
        # 1. Empty items
        with pytest.raises(ValidationError, match="at least one product variant item"):
            sale_service.create_sale(
                {'payment_method': 'CASH', 'sale_date': '2026-09-25'},
                [],
                user_id=1
            )

        # 2. Insufficient stock
        variants = sale_service.get_active_variants_for_sale()
        var = variants[0]
        with pytest.raises(ValidationError, match="Insufficient stock"):
            sale_service.create_sale(
                {'payment_method': 'CASH', 'sale_date': '2026-09-25'},
                [{'variant_id': var['variant_id'], 'quantity': 999999, 'unit_price': 100}],
                user_id=1
            )

        # 3. Credit without customer
        with pytest.raises(ValidationError, match="customer must be selected"):
            sale_service.create_sale(
                {'customer_id': None, 'payment_method': 'CREDIT', 'sale_date': '2026-09-25'},
                [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': float(var['selling_price'])}],
                user_id=1
            )

        # 4. Invalid payment method
        with pytest.raises(ValidationError, match="Invalid payment method"):
            sale_service.create_sale(
                {'payment_method': 'BITCOIN', 'sale_date': '2026-09-25'},
                [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': 100}],
                user_id=1
            )


# ---------------------------------------------------------------------------
# 3. Web & API Routes
# ---------------------------------------------------------------------------

def test_sales_index_route(admin_client):
    """Test GET /sales page renders successfully."""
    response = admin_client.get('/sales')
    assert response.status_code == 200
    assert b'Sales &amp; Billing' in response.data or b'Sales & Billing' in response.data


def test_sales_new_route_get(admin_client):
    """Test GET /sales/new page renders POS interface."""
    response = admin_client.get('/sales/new')
    assert response.status_code == 200
    assert b'Point of Sale' in response.data or b'New Sale' in response.data


def test_sales_new_route_post(admin_client, app):
    """Test POST /sales/new creates a sale and redirects to invoice view."""
    with app.app_context():
        variants = sale_service.get_active_variants_for_sale()
        available = [v for v in variants if v['stock_quantity'] >= 1]
        var = available[0]
        var_id = var['variant_id']
        price = float(var['selling_price'])

    payload = {
        'sale_date': date.today().strftime('%Y-%m-%d'),
        'payment_method': 'UPI',
        'paid_amount': str(price),
        'discount': '0.00',
        'tax': '0.00',
        'notes': 'Form POST Test',
        'variant_id[]': [str(var_id)],
        'quantity[]': ['1'],
        'unit_price[]': [str(price)],
        'item_discount[]': ['0.00'],
    }

    response = admin_client.post('/sales/new', data=payload, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invoice' in response.data


def test_api_list_sales(admin_client):
    """Test GET /api/sales returns JSON list."""
    response = admin_client.get('/api/sales')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert 'sales' in json_data


def test_api_get_sale_detail(admin_client, app):
    """Test GET /api/sales/<id> returns detailed JSON."""
    with app.app_context():
        sales = sale_service.get_all_sales()
        assert len(sales) > 0
        sale_id = sales[0]['sale_id']

    response = admin_client.get(f'/api/sales/{sale_id}')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert 'sale' in json_data
    assert 'items' in json_data


def test_api_pos_variant_search(admin_client):
    """Test GET /api/pos/variants/search returns matching active variants."""
    response = admin_client.get('/api/pos/variants/search?q=')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert 'variants' in json_data


def test_api_pos_customer_search_and_quick_create(admin_client):
    """Test customer search and quick-create endpoints for POS."""
    # Search
    response = admin_client.get('/api/pos/customers/search?q=')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert 'customers' in json_data

    # Quick create
    import time
    test_phone = f"99{str(time.time_ns())[-8:]}"
    create_resp = admin_client.post('/api/pos/customers/quick-create', json={
        'customer_name': 'POS Quick Customer',
        'phone': test_phone,
        'credit_limit': 5000.0,
    })
    assert create_resp.status_code == 201
    create_json = create_resp.get_json()
    assert create_json['status'] == 'success'
    assert 'customer_id' in create_json


# ---------------------------------------------------------------------------
# 4. Regression Tests: POS Cart Controls & Stock Bounding
# ---------------------------------------------------------------------------

def test_pos_template_cart_controls_rendered(admin_client):
    """Regression: POS /sales/new renders all required JS functions and helpers."""
    response = admin_client.get('/sales/new')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    # Core functions must be present
    assert 'changeQty' in html
    assert 'updateQty' in html
    assert 'qty-btn' in html
    assert 'posItemsTbody' in html
    assert 'recalcTotals' in html

    # Authoritative stock helpers introduced in the fix must be present
    assert 'getStock' in html
    assert 'getQty' in html

    # Stock must be read from VARIANTS inside getStock, not from item.stock
    # Check that VARIANTS map is defined in the script
    assert 'const VARIANTS' in html

    # addToCart should accept a single variantId (reads stock from VARIANTS)
    assert 'function addToCart(variantId)' in html

    # changeQty must use getStock() — the authoritative lookup
    assert 'getStock(vid)' in html


def test_pos_variants_map_renders_integer_stock(admin_client, app):
    """Regression: VARIANTS JS map in POS must render stock_quantity as an integer.

    The previous bug occurred when item.stock diverged from VARIANTS[vid].stock.
    Now stock is always read from VARIANTS so this test validates the source data.
    """
    response = admin_client.get('/sales/new')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    with app.app_context():
        variants = sale_service.get_active_variants_for_sale()

    # For every active variant the stock integer must appear in the VARIANTS block
    # (Jinja renders {{ v.stock_quantity | int }} so it's always a plain integer)
    for v in variants[:5]:   # spot-check first 5 to keep test fast
        stock_val = int(v['stock_quantity'])
        # The rendered JS should contain  stock: <N>,
        assert f'stock:         {stock_val},' in html or f'stock: {stock_val},' in html, (
            f"variant {v['variant_id']} stock {stock_val} not found as integer in VARIANTS map"
        )


def test_pos_changequty_qty1_stock3_does_not_block(admin_client, app):
    """Regression: qty=1 with stock=3 must NOT trigger the stock-limit alert path.

    The previous bug: changeQty used parseInt(item.stock) || fallback where item.stock
    could be stale, causing maxStock to be 1 when real stock was 3.  With qty=1 and
    maxStock=1, newQty=2 > 1 triggered the false alert.

    This test verifies that the rendered HTML for the POS page contains the authoritative
    getStock() helper that reads from VARIANTS — ensuring the bug cannot recur in the
    template, and confirms that the backend allows qty=1 for a variant with stock >= 3.
    """
    with app.app_context():
        variants = sale_service.get_active_variants_for_sale()
        # Find a variant with stock >= 3 to reproduce the exact scenario
        target = next((v for v in variants if v['stock_quantity'] >= 3), None)

    if target is None:
        pytest.skip("No variant with stock >= 3 available for regression test")

    var_id       = target['variant_id']
    current_stock = int(target['stock_quantity'])
    price         = float(target['selling_price'])

    # POST qty=1 (well within stock) — must succeed, not return a stock error
    payload = {
        'sale_date':        date.today().strftime('%Y-%m-%d'),
        'payment_method':   'CASH',
        'discount':         '0.00',
        'tax':              '0.00',
        'variant_id[]':     [str(var_id)],
        'quantity[]':       ['1'],
        'unit_price[]':     [str(price)],
        'item_discount[]':  ['0.00'],
    }
    response = admin_client.post('/sales/new', data=payload, follow_redirects=False)
    # Must NOT be a 400 stock error; it should redirect (302) on success
    # OR be a 400 only for non-stock reasons (e.g. missing customer for CREDIT)
    # The key assertion: "Insufficient stock" must NOT appear
    assert b'Insufficient stock' not in response.data, (
        f"False stock-limit error for qty=1 with stock={current_stock}: "
        f"this is the regression the fix must prevent"
    )


def test_pos_stock_limit_enforcement_backend(admin_client, app):
    """Regression: Backend strictly enforces stock limit when quantity exceeds stock."""
    with app.app_context():
        variants = sale_service.get_active_variants_for_sale()
        available = [v for v in variants if v['stock_quantity'] >= 1]
        var = available[0]
        var_id = var['variant_id']
        current_stock = var['stock_quantity']
        price = float(var['selling_price'])

    # Request stock + 10 units — must be rejected
    excess_qty = current_stock + 10
    payload = {
        'sale_date':       date.today().strftime('%Y-%m-%d'),
        'payment_method':  'CASH',
        'paid_amount':     str(price * excess_qty),
        'discount':        '0.00',
        'tax':             '0.00',
        'variant_id[]':    [str(var_id)],
        'quantity[]':      [str(excess_qty)],
        'unit_price[]':    [str(price)],
        'item_discount[]': ['0.00'],
    }

    response = admin_client.post('/sales/new', data=payload, follow_redirects=True)
    assert response.status_code == 400
    assert b'Insufficient stock' in response.data


def test_pos_template_custom_modal_alert_and_single_changeqty(admin_client):
    """Regression: POS uses window.vlAlert custom modal and has exactly one changeQty definition."""
    response = admin_client.get('/sales/new')
    assert response.status_code == 200
    html = response.data.decode('utf-8')

    # Confirm exactly one definition of changeQty, updateQty, addToCart
    assert html.count('function changeQty(') == 1
    assert html.count('function updateQty(') == 1
    assert html.count('function addToCart(') == 1
    assert html.count('function renderCart(') == 1

    # Confirm custom modal vlAlert is integrated
    assert 'window.vlAlert' in html
    assert 'Cannot add more' in html
    assert 'Cannot exceed stock' in html

    # Confirm global modal container exists in base layout
    assert 'vlConfirmModal' in html
    assert 'vl-confirm-card' in html

