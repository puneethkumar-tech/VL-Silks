import time
import pytest
from decimal import Decimal
from datetime import date
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import customer_service, sale_service
from backend.services.customer_service import ValidationError


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


_counter = 0

def unique_phone():
    """Generate a unique phone number for test isolation."""
    global _counter
    _counter += 1
    t = int(time.time() * 1000) % 1000000
    return f"98{t:06d}{_counter:02d}"


# ---------------------------------------------------------------------------
# 1. Customer Service — List, Search, Summary Metrics
# ---------------------------------------------------------------------------

def test_get_customers_list(app):
    """1. Customer list retrieval with aggregated statistics."""
    with app.app_context():
        customers = customer_service.get_customers()
        assert isinstance(customers, list)
        assert len(customers) >= 1
        first = customers[0]
        assert 'customer_id' in first
        assert 'customer_name' in first
        assert 'phone' in first
        assert 'total_purchases' in first
        assert 'total_purchase_value' in first
        assert 'total_paid' in first
        assert 'outstanding_balance' in first


def test_customer_summary_metrics(app):
    """2. Customer summary metrics calculation."""
    with app.app_context():
        metrics = customer_service.get_customer_summary_metrics()
        assert 'total_customers' in metrics
        assert 'active_customers' in metrics
        assert 'customers_with_balance' in metrics
        assert 'total_outstanding' in metrics
        assert metrics['total_customers'] >= metrics['active_customers']


def test_customer_search_by_name(app):
    """3. Customer search by customer name."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'UniqueSearchableCustomerName',
            'phone': phone,
        })
        try:
            results = customer_service.get_customers(search='UniqueSearchable')
            assert len(results) >= 1
            assert any(c['customer_id'] == cust_id for c in results)
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_search_by_phone(app):
    """4. Customer search by phone number (mandatory)."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'PhoneSearchCustomer',
            'phone': phone,
        })
        try:
            results = customer_service.get_customers(search=phone)
            assert len(results) >= 1
            assert any(c['customer_id'] == cust_id for c in results)
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_search_by_email(app):
    """5. Customer search by email address."""
    with app.app_context():
        phone = unique_phone()
        email = f"search_{phone}@vlsilkstest.com"
        cust_id = customer_service.create_customer({
            'customer_name': 'EmailSearchCustomer',
            'phone': phone,
            'email': email,
        })
        try:
            results = customer_service.get_customers(search=email)
            assert len(results) >= 1
            assert any(c['customer_id'] == cust_id for c in results)
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_status_filter(app):
    """6. Active/inactive filter support."""
    with app.app_context():
        active_list = customer_service.get_customers(status='ACTIVE')
        assert all(c['status'] == 'ACTIVE' for c in active_list)

        inactive_list = customer_service.get_customers(status='INACTIVE')
        assert all(c['status'] == 'INACTIVE' for c in inactive_list)


def test_get_customer_by_id(app):
    """7. Customer detail retrieval with profile and available credit."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'DetailCustomer',
            'phone': phone,
            'credit_limit': 30000.0,
        })
        try:
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust is not None
            assert cust['customer_name'] == 'DetailCustomer'
            assert cust['phone'] == phone
            assert 'available_credit' in cust
            assert cust['available_credit'] <= Decimal('30000.00')
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_get_customer_by_invalid_id(app):
    """19. Invalid customer ID handling."""
    with app.app_context():
        assert customer_service.get_customer_by_id(None) is None
        assert customer_service.get_customer_by_id(9999999) is None
        assert customer_service.get_customer_by_id("invalid-id") is None


# ---------------------------------------------------------------------------
# 2. Purchase History & Financial Calculations (No double counting)
# ---------------------------------------------------------------------------

def test_customer_with_no_purchases(app):
    """9. Customer with no purchases has 0 statistics."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'ZeroPurchaseCustomer',
            'phone': phone,
        })
        try:
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['total_purchases'] == 0
            assert Decimal(str(cust['total_purchase_value'])) == Decimal('0.00')
            assert Decimal(str(cust['total_paid'])) == Decimal('0.00')
            assert Decimal(str(cust['outstanding_balance'])) == Decimal('0.00')

            history = customer_service.get_customer_purchase_history(cust_id)
            assert len(history) == 0
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_with_single_purchase(app):
    """10. Customer with one purchase."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'SinglePurchaseCustomer',
            'phone': phone,
        })

        # Create one sale for this customer
        variants = sale_service.get_active_variants_for_sale()
        var = variants[0]
        unit_price = Decimal(str(var['selling_price']))

        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CASH',
            'paid_amount': float(unit_price),
            'discount': 0.0,
            'tax': 0.0,
            'notes': 'Single purchase test',
        }
        items_data = [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': float(unit_price)}]

        sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
        try:
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['total_purchases'] == 1
            assert Decimal(str(cust['total_purchase_value'])) == unit_price
            assert Decimal(str(cust['total_paid'])) == unit_price
            assert Decimal(str(cust['outstanding_balance'])) == Decimal('0.00')

            history = customer_service.get_customer_purchase_history(cust_id)
            assert len(history) == 1
            assert history[0]['sale_id'] == sale_id
            assert history[0]['item_count'] == 1
        finally:
            # Clean up
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'SALE' AND reference_id = %s", (sale_id,))
                cursor.execute("DELETE FROM payments WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sale_items WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_purchase_total_aggregation_no_item_duplicate(app):
    """11, 12, 13, 14, 15. Verify multiple items & split payments do NOT double-count sales totals."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'MultiItemCustomer',
            'phone': phone,
        })

        variants = sale_service.get_active_variants_for_sale()
        var1 = variants[0]
        var2 = variants[1] if len(variants) > 1 else variants[0]

        price1 = Decimal(str(var1['selling_price']))
        price2 = Decimal(str(var2['selling_price']))
        total_expected = price1 + price2

        # 1 sale with 2 different items (or 2 units)
        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CREDIT',
            'paid_amount': 0.0,
            'discount': 0.0,
            'tax': 0.0,
            'notes': 'Multi item aggregation test',
        }
        items_data = [
            {'variant_id': var1['variant_id'], 'quantity': 1, 'unit_price': float(price1)},
            {'variant_id': var2['variant_id'], 'quantity': 1, 'unit_price': float(price2)} if var1['variant_id'] != var2['variant_id'] else {'variant_id': var1['variant_id'], 'quantity': 2, 'unit_price': float(price1)}
        ]
        if var1['variant_id'] == var2['variant_id']:
            total_expected = price1 * 2

        sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
        try:
            cust = customer_service.get_customer_by_id(cust_id)
            # Total purchase value must equal exact sale total, NOT multiplied by join rows
            assert cust['total_purchases'] == 1
            assert Decimal(str(cust['total_purchase_value'])) == total_expected
            assert Decimal(str(cust['outstanding_balance'])) == total_expected
            assert Decimal(str(cust['total_paid'])) == Decimal('0.00')

            history = customer_service.get_customer_purchase_history(cust_id)
            assert len(history) == 1
            assert history[0]['item_count'] == len(items_data)
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'SALE' AND reference_id = %s", (sale_id,))
                cursor.execute("DELETE FROM credit_transactions WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sale_items WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


# ---------------------------------------------------------------------------
# 3. Customer Validation & Error Handling
# ---------------------------------------------------------------------------

def test_create_customer_success(app):
    """20. Customer creation."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Valid New Customer',
            'phone': phone,
            'email': 'valid.customer@example.com',
            'address': '42 Silk Street, Kanchipuram',
            'credit_limit': 35000.0,
            'status': 'ACTIVE',
        })
        assert cust_id > 0
        try:
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['customer_name'] == 'Valid New Customer'
            assert cust['phone'] == phone
            assert cust['email'] == 'valid.customer@example.com'
            assert cust['address'] == '42 Silk Street, Kanchipuram'
            assert Decimal(str(cust['credit_limit'])) == Decimal('35000.00')
            assert cust['status'] == 'ACTIVE'
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_create_customer_missing_name(app):
    """18. Missing name rejection."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Customer name is required"):
            customer_service.create_customer({
                'customer_name': '   ',
                'phone': unique_phone(),
            })


def test_create_customer_missing_phone(app):
    """Phone requirement validation."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Customer phone number is required"):
            customer_service.create_customer({
                'customer_name': 'No Phone Customer',
                'phone': '',
            })


def test_create_customer_duplicate_phone(app):
    """16. Duplicate phone rejection."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Customer One',
            'phone': phone,
        })
        try:
            with pytest.raises(ValidationError, match="already exists"):
                customer_service.create_customer({
                    'customer_name': 'Customer Two Duplicate Phone',
                    'phone': phone,
                })
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_create_customer_invalid_email(app):
    """17. Invalid email rejection."""
    with app.app_context():
        with pytest.raises(ValidationError, match="Invalid email address format"):
            customer_service.create_customer({
                'customer_name': 'Bad Email Customer',
                'phone': unique_phone(),
                'email': 'not-an-email-at-all',
            })


def test_create_customer_negative_credit_limit(app):
    """Negative credit limit rejection."""
    with app.app_context():
        with pytest.raises(ValidationError, match="cannot be negative"):
            customer_service.create_customer({
                'customer_name': 'Negative Limit Customer',
                'phone': unique_phone(),
                'credit_limit': -500.0,
            })


# ---------------------------------------------------------------------------
# 4. Customer Update & Status
# ---------------------------------------------------------------------------

def test_update_customer_success(app):
    """21. Update customer."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Original Name',
            'phone': phone,
            'credit_limit': 15000.0,
        })
        try:
            customer_service.update_customer(cust_id, {
                'customer_name': 'Updated Name',
                'phone': phone,
                'email': 'updated@example.com',
                'address': 'New Address',
                'credit_limit': 20000.0,
                'status': 'ACTIVE',
            })
            updated = customer_service.get_customer_by_id(cust_id)
            assert updated['customer_name'] == 'Updated Name'
            assert updated['email'] == 'updated@example.com'
            assert Decimal(str(updated['credit_limit'])) == Decimal('20000.00')
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_update_same_customer_phone(app):
    """22. Update same customer's phone allowed."""
    with app.app_context():
        phone1 = unique_phone()
        phone2 = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Phone Update Customer',
            'phone': phone1,
        })
        try:
            # Retain same phone
            customer_service.update_customer(cust_id, {
                'customer_name': 'Phone Update Customer',
                'phone': phone1,
            })
            # Change to new unique phone
            customer_service.update_customer(cust_id, {
                'customer_name': 'Phone Update Customer',
                'phone': phone2,
            })
            updated = customer_service.get_customer_by_id(cust_id)
            assert updated['phone'] == phone2
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_update_duplicate_phone_rejected(app):
    """23. Duplicate phone on update rejected."""
    with app.app_context():
        phone1 = unique_phone()
        phone2 = unique_phone()
        cust1 = customer_service.create_customer({'customer_name': 'Cust 1', 'phone': phone1})
        cust2 = customer_service.create_customer({'customer_name': 'Cust 2', 'phone': phone2})
        try:
            # Try to update cust2's phone to cust1's phone
            with pytest.raises(ValidationError, match="already exists"):
                customer_service.update_customer(cust2, {
                    'customer_name': 'Cust 2',
                    'phone': phone1,
                })
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id IN (%s, %s)", (cust1, cust2))


def test_toggle_customer_status(app):
    """24. Safe customer deactivation toggle."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Toggle Status Customer',
            'phone': phone,
            'status': 'ACTIVE',
        })
        try:
            new_st = customer_service.toggle_customer_status(cust_id)
            assert new_st == 'INACTIVE'
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['status'] == 'INACTIVE'

            new_st2 = customer_service.toggle_customer_status(cust_id)
            assert new_st2 == 'ACTIVE'
            cust2 = customer_service.get_customer_by_id(cust_id)
            assert cust2['status'] == 'ACTIVE'
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_safe_deactivation_preserves_historical_records(app):
    """25, 26, 27. Historical sales, payments & credit transactions preserved after deactivation."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'Historical Records Customer',
            'phone': phone,
            'status': 'ACTIVE',
        })

        variants = sale_service.get_active_variants_for_sale()
        var = variants[0]
        unit_price = Decimal(str(var['selling_price']))

        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CREDIT',
            'paid_amount': 0.0,
            'discount': 0.0,
            'tax': 0.0,
            'notes': 'Historical preserve test',
        }
        items_data = [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': float(unit_price)}]
        sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)

        try:
            # Deactivate customer
            customer_service.delete_customer(cust_id)

            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['status'] == 'INACTIVE'

            # 25. Sale still exists
            sale = sale_service.get_sale_by_id(sale_id)
            assert sale is not None
            assert sale['customer_id'] == cust_id

            # 26. Sale items still exist
            items = sale_service.get_sale_items(sale_id)
            assert len(items) >= 1

            # 27. Credit transaction still exists
            credit_tx = query_db(
                "SELECT * FROM credit_transactions WHERE sale_id = %s", (sale_id,), one=True
            )
            assert credit_tx is not None
            assert credit_tx['customer_id'] == cust_id
        finally:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'SALE' AND reference_id = %s", (sale_id,))
                cursor.execute("DELETE FROM credit_transactions WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sale_items WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


# ---------------------------------------------------------------------------
# 5. Role Access & Web Routes
# ---------------------------------------------------------------------------

def test_unauthenticated_web_access_redirects(client):
    """30. Unauthenticated access redirects to login."""
    res = client.get('/customers')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']


def test_staff_web_access(staff_client):
    """28. Staff access — can view directory, search, profile, purchase history."""
    # List
    res_list = staff_client.get('/customers')
    assert res_list.status_code == 200
    assert b'Customer Directory' in res_list.data

    # Profile view
    res_view = staff_client.get('/customers/1')
    assert res_view.status_code in (200, 302)

    # Purchases view
    res_purchases = staff_client.get('/customers/1/purchases')
    assert res_purchases.status_code in (200, 302)

    # Denied from adding
    res_new = staff_client.get('/customers/new', follow_redirects=True)
    assert b'Administrator access required' in res_new.data

    # Denied from editing
    res_edit = staff_client.get('/customers/1/edit', follow_redirects=True)
    assert b'Administrator access required' in res_edit.data


def test_admin_web_access_full_crud(admin_client, app):
    """29. Admin access — can create, edit, view, toggle customers."""
    phone = unique_phone()

    # GET /customers/new
    res_new = admin_client.get('/customers/new')
    assert res_new.status_code == 200
    assert b'Register New Customer' in res_new.data

    # POST /customers/new
    res_create = admin_client.post('/customers/new', data={
        'customer_name': 'Web Created Customer',
        'phone': phone,
        'email': 'webcreated@example.com',
        'address': 'Web Address',
        'credit_limit': '25000.00',
        'status': 'ACTIVE',
    }, follow_redirects=True)
    assert res_create.status_code == 200
    assert b'Web Created Customer' in res_create.data

    # Get created customer ID
    with app.app_context():
        cust = query_db("SELECT customer_id FROM customers WHERE phone = %s", (phone,), one=True)
        cust_id = cust['customer_id']

    try:
        # GET /customers/<id>/edit
        res_edit = admin_client.get(f'/customers/{cust_id}/edit')
        assert res_edit.status_code == 200
        assert b'Edit Customer' in res_edit.data

        # POST /customers/<id>/edit
        res_update = admin_client.post(f'/customers/{cust_id}/edit', data={
            'customer_name': 'Web Created Customer UPDATED',
            'phone': phone,
            'credit_limit': '30000.00',
            'status': 'ACTIVE',
        }, follow_redirects=True)
        assert res_update.status_code == 200
        assert b'UPDATED' in res_update.data

        # POST /customers/<id>/toggle-status
        res_toggle = admin_client.post(f'/customers/{cust_id}/toggle-status', follow_redirects=True)
        assert res_toggle.status_code == 200

        with app.app_context():
            updated = customer_service.get_customer_by_id(cust_id)
            assert updated['status'] == 'INACTIVE'
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_web_customer_not_found_redirects(admin_client):
    """Non-existent customer ID redirects to list."""
    res = admin_client.get('/customers/999999', follow_redirects=True)
    assert res.status_code == 200
    assert b'not found' in res.data


# ---------------------------------------------------------------------------
# 6. REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_customers_list(client):
    """31. API customer list endpoint."""
    res = client.get('/api/customers')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'data' in data
    assert 'count' in data


def test_api_customers_search_by_phone(client, app):
    """API customer search with phone parameter."""
    phone = unique_phone()
    with app.app_context():
        cust_id = customer_service.create_customer({
            'customer_name': 'ApiSearchCustomer',
            'phone': phone,
        })
    try:
        res = client.get(f'/api/customers?phone={phone}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['count'] >= 1
        assert any(c['customer_id'] == cust_id for c in data['data'])
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_api_customer_detail(client, app):
    """32. API customer detail endpoint."""
    phone = unique_phone()
    with app.app_context():
        cust_id = customer_service.create_customer({
            'customer_name': 'ApiDetailCustomer',
            'phone': phone,
        })
    try:
        res = client.get(f'/api/customers/{cust_id}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert data['data']['customer_name'] == 'ApiDetailCustomer'
        assert 'purchases' in data
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_api_customer_detail_not_found(client):
    """API customer detail 404 for invalid ID."""
    res = client.get('/api/customers/999999')
    assert res.status_code == 404
    data = res.get_json()
    assert data['status'] == 'error'


def test_api_admin_create_update_delete_customer(admin_client, app):
    """33, 34, 35. API customer create, update, and safe deactivation."""
    phone = unique_phone()

    # 33. POST /api/customers
    res_create = admin_client.post('/api/customers', json={
        'customer_name': 'API Full Test Customer',
        'phone': phone,
        'email': 'apifull@example.com',
        'address': 'API Street',
        'credit_limit': 18000.0,
    })
    assert res_create.status_code == 201
    create_data = res_create.get_json()
    assert create_data['status'] == 'success'
    cust_id = create_data['customer_id']

    try:
        # 34. PUT /api/customers/<id>
        res_update = admin_client.put(f'/api/customers/{cust_id}', json={
            'customer_name': 'API Full Test Customer RENAMED',
            'phone': phone,
            'credit_limit': 22000.0,
        })
        assert res_update.status_code == 200
        update_data = res_update.get_json()
        assert update_data['data']['customer_name'] == 'API Full Test Customer RENAMED'

        # 35. DELETE /api/customers/<id> (Safe deactivation)
        res_delete = admin_client.delete(f'/api/customers/{cust_id}')
        assert res_delete.status_code == 200
        assert 'safely deactivated' in res_delete.get_json()['message']

        # Verify DB status is INACTIVE
        with app.app_context():
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust['status'] == 'INACTIVE'
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_api_create_customer_unauthorized(client):
    """Unauthorized non-admin POST to /api/customers rejected with 403."""
    res = client.post('/api/customers', json={
        'customer_name': 'Unauthorized Customer',
        'phone': unique_phone(),
    })
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# 7. POS Compatibility & Phase 9 Integration
# ---------------------------------------------------------------------------

def test_update_customer_not_found(app):
    """Update non-existent customer raises ValidationError."""
    with app.app_context():
        with pytest.raises(ValidationError, match="not found"):
            customer_service.update_customer(9999999, {
                'customer_name': 'Ghost Customer',
                'phone': unique_phone(),
            })


def test_api_admin_update_customer_validation_error(admin_client, app):
    """38. Validation error on API update returns 400."""
    phone = unique_phone()
    with app.app_context():
        cust_id = customer_service.create_customer({
            'customer_name': 'ApiValCust',
            'phone': phone,
        })
    try:
        # Invalid email
        res = admin_client.put(f'/api/customers/{cust_id}', json={
            'customer_name': 'ApiValCust',
            'phone': phone,
            'email': 'invalid-email-format',
        })
        assert res.status_code == 400
        assert 'Invalid email' in res.get_json()['message']
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_customer_purchases_route(admin_client):
    """GET /customers/<id>/purchases dedicated purchase history page renders."""
    res = admin_client.get('/customers/1/purchases')
    assert res.status_code in (200, 302)
    if res.status_code == 200:
        assert b'Invoice History' in res.data or b'Purchase History' in res.data


def test_pos_customer_search_preserved(client):
    """36. POS customer search (/api/pos/customers/search) still functional."""
    res = client.get('/api/pos/customers/search?q=')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'customers' in data
    assert isinstance(data['customers'], list)
    if len(data['customers']) > 0:
        c = data['customers'][0]
        assert 'customer_id' in c
        assert 'current_balance' in c
        assert 'available_credit' in c


def test_pos_quick_create_preserved(client, app):
    """37. POS quick-create (/api/pos/customers/quick-create) still functional."""
    phone = unique_phone()
    res = client.post('/api/pos/customers/quick-create', json={
        'customer_name': 'POS Preserved Customer',
        'phone': phone,
        'credit_limit': 15000.0,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['status'] == 'success'
    cust_id = data['customer_id']

    try:
        with app.app_context():
            cust = customer_service.get_customer_by_id(cust_id)
            assert cust is not None
            assert cust['customer_name'] == 'POS Preserved Customer'
            assert cust['status'] == 'ACTIVE'
    finally:
        with app.app_context():
            with get_db_cursor(commit=True) as cursor:
                cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))

