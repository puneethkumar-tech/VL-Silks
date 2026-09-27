import time
import pytest
from decimal import Decimal
from datetime import date
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import credit_service, customer_service, sale_service
from backend.services.credit_service import ValidationError, to_decimal

_phone_counter = 0


def unique_phone():
    """Generate isolated unique phone numbers for test data."""
    global _phone_counter
    _phone_counter += 1
    t = int(time.time() * 1000) % 1000000
    return f"97{t:06d}{_phone_counter:02d}"


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


def create_test_customer_with_credit(credit_amount=Decimal('5000.00'), credit_limit=Decimal('25000.00')):
    """Helper to create an isolated customer and an authentic credit sale."""
    phone = unique_phone()
    cust_id = customer_service.create_customer({
        'customer_name': f'CreditTestCust_{phone}',
        'phone': phone,
        'credit_limit': float(credit_limit),
        'status': 'ACTIVE'
    })

    variants = sale_service.get_active_variants_for_sale()
    var = variants[0]

    sale_data = {
        'customer_id': cust_id,
        'sale_date': date.today().strftime('%Y-%m-%d'),
        'payment_method': 'CREDIT',
        'paid_amount': 0.0,
        'discount': 0.0,
        'tax': 0.0,
        'notes': 'Test Credit Sale',
    }
    items_data = [{
        'variant_id': var['variant_id'],
        'quantity': 1,
        'unit_price': float(credit_amount),
        'item_discount': 0.0
    }]
    sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
    return cust_id, sale_id, credit_amount


def cleanup_test_records(customer_ids=None, sale_ids=None):
    """Helper to clean up test transactions, payments, sales, and customers."""
    with get_db_cursor(commit=True) as cursor:
        if sale_ids:
            format_s = ','.join(['%s'] * len(sale_ids))
            # Restore stock quantity before deleting sale items
            cursor.execute(f"SELECT variant_id, quantity FROM sale_items WHERE sale_id IN ({format_s})", tuple(sale_ids))
            sold_items = cursor.fetchall()
            for it in sold_items:
                cursor.execute("UPDATE product_variants SET stock_quantity = stock_quantity + %s WHERE variant_id = %s", (it['quantity'], it['variant_id']))
            cursor.execute(f"DELETE FROM stock_movements WHERE reference_type = 'SALE' AND reference_id IN ({format_s})", tuple(sale_ids))
            cursor.execute(f"DELETE FROM credit_transactions WHERE sale_id IN ({format_s})", tuple(sale_ids))
            cursor.execute(f"DELETE FROM payments WHERE sale_id IN ({format_s})", tuple(sale_ids))
            cursor.execute(f"DELETE FROM sale_items WHERE sale_id IN ({format_s})", tuple(sale_ids))
            cursor.execute(f"DELETE FROM sales WHERE sale_id IN ({format_s})", tuple(sale_ids))
        if customer_ids:
            format_c = ','.join(['%s'] * len(customer_ids))
            cursor.execute(f"DELETE FROM credit_transactions WHERE customer_id IN ({format_c})", tuple(customer_ids))
            cursor.execute(f"DELETE FROM payments WHERE customer_id IN ({format_c})", tuple(customer_ids))
            cursor.execute(f"DELETE FROM customers WHERE customer_id IN ({format_c})", tuple(customer_ids))


# ---------------------------------------------------------------------------
# 1. Summary & Metric Calculations
# ---------------------------------------------------------------------------

def test_credit_summary_loads(app):
    """1. Credit summary returns all required statistical fields."""
    with app.app_context():
        summary = credit_service.get_credit_summary()
        assert 'total_credit_customers' in summary
        assert 'total_credit_to_collect' in summary
        assert 'total_credit_sales_amount' in summary
        assert 'total_settlements_amount' in summary
        assert 'total_credit_sales_count' in summary
        assert 'total_settlements_count' in summary
        assert summary['total_credit_to_collect'] >= Decimal('0.00')


def test_total_credit_matches_database(app):
    """2. Total credit matches direct database transaction calculation."""
    with app.app_context():
        summary = credit_service.get_credit_summary()
        direct_total = credit_service.calculate_total_credit_outstanding()
        assert summary['total_credit_to_collect'] == direct_total


def test_credit_customer_count_correct(app):
    """3. Total credit customer count matches count of customers with positive balance."""
    with app.app_context():
        summary = credit_service.get_credit_summary()
        customers = credit_service.get_credit_customers()
        assert summary['total_credit_customers'] == len(customers)


# ---------------------------------------------------------------------------
# 2. Customer Directory & Filters
# ---------------------------------------------------------------------------

def test_credit_customers_directory_returned(app):
    """4. Outstanding customers directory returned with valid balances."""
    with app.app_context():
        customers = credit_service.get_credit_customers()
        assert isinstance(customers, list)
        for c in customers:
            assert c['outstanding_balance'] > Decimal('0.00')
            assert c['available_credit'] >= Decimal('0.00')
            assert 'last_transaction_date' in c


def test_zero_balance_customer_excluded_from_directory(app):
    """5. Zero balance customer is excluded from default credit directory."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'ZeroBalCust',
            'phone': phone,
        })
        try:
            customers = credit_service.get_credit_customers()
            assert not any(c['customer_id'] == cust_id for c in customers)
        finally:
            cleanup_test_records(customer_ids=[cust_id])


def test_credit_customers_search_by_name_and_phone(app):
    """6, 7. Credit customer search by name and phone number."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3000.00'))
        cust = customer_service.get_customer_by_id(cust_id)
        try:
            # Search by name
            res_name = credit_service.get_credit_customers(search=cust['customer_name'])
            assert any(c['customer_id'] == cust_id for c in res_name)

            # Search by phone
            res_phone = credit_service.get_credit_customers(search=cust['phone'])
            assert any(c['customer_id'] == cust_id for c in res_phone)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_credit_customers_status_filter(app):
    """8. Credit customer status filtering (ACTIVE vs INACTIVE)."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('2500.00'))
        customer_service.toggle_customer_status(cust_id)  # Make INACTIVE
        try:
            inactive_list = credit_service.get_credit_customers(status='INACTIVE')
            assert any(c['customer_id'] == cust_id for c in inactive_list)

            active_list = credit_service.get_credit_customers(status='ACTIVE')
            assert not any(c['customer_id'] == cust_id for c in active_list)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


# ---------------------------------------------------------------------------
# 3. Customer Credit Profile & Calculations
# ---------------------------------------------------------------------------

def test_customer_credit_profile_data(app):
    """9. Customer credit profile retrieval with financial metrics."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(Decimal('4500.00'))
        try:
            profile = credit_service.get_customer_credit_profile(cust_id)
            assert profile is not None
            assert profile['customer_id'] == cust_id
            assert profile['outstanding_balance'] == amt
            assert profile['total_credit_amount'] == amt
            assert profile['total_paid_amount'] == Decimal('0.00')
            assert profile['available_credit'] == Decimal('25000.00') - amt
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_customer_credit_profile_not_found(app):
    """10. Non-existent customer ID returns None."""
    with app.app_context():
        assert credit_service.get_customer_credit_profile(None) is None
        assert credit_service.get_customer_credit_profile(9999999) is None
        assert credit_service.get_customer_credit_profile("invalid-id") is None


def test_customer_no_credit_history_profile(app):
    """11. Customer with no credit history has 0 balance and full credit limit available."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'NoCreditHistoryCust',
            'phone': phone,
            'credit_limit': 20000.0
        })
        try:
            profile = credit_service.get_customer_credit_profile(cust_id)
            assert profile['outstanding_balance'] == Decimal('0.00')
            assert profile['available_credit'] == Decimal('20000.00')
            assert profile['total_credit_sales_count'] == 0
            assert profile['settlements_count'] == 0
        finally:
            cleanup_test_records(customer_ids=[cust_id])


def test_outstanding_balance_calculation_accuracy(app):
    """12. Outstanding balance = total charges - total settlements."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(Decimal('6000.00'))
        try:
            bal1 = credit_service.get_customer_outstanding_balance(cust_id)
            assert bal1 == Decimal('6000.00')

            # Record part settlement of 2,000
            credit_service.record_credit_payment(cust_id, {
                'amount': '2000.00',
                'payment_method': 'UPI'
            }, user_id=1)

            bal2 = credit_service.get_customer_outstanding_balance(cust_id)
            assert bal2 == Decimal('4000.00')
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


# ---------------------------------------------------------------------------
# 4. Chronological Ledger & Running Balances
# ---------------------------------------------------------------------------

def test_ledger_credit_sale_and_settlement_appear(app):
    """13, 14. Credit sale and settlement payment appear in ledger."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(Decimal('5000.00'))
        try:
            pay_res = credit_service.record_credit_payment(cust_id, {
                'amount': '1500.00',
                'payment_method': 'CASH',
                'notes': 'Ledger cash settlement'
            }, user_id=1)

            ledger = credit_service.get_customer_credit_history(cust_id)
            assert len(ledger) == 2

            tx_types = [row['transaction_type'] for row in ledger]
            assert 'CREDIT_SALE' in tx_types
            assert 'PAYMENT' in tx_types
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_ledger_chronological_ordering_and_running_balance(app):
    """15, 16, 17, 18, 19, 20. Chronological ordering, running balance & mixed sequences."""
    with app.app_context():
        cust_id, sale_id1, amt1 = create_test_customer_with_credit(Decimal('4000.00'))

        # Create second credit sale of 2,000
        variants = sale_service.get_active_variants_for_sale()
        var = variants[0]
        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CREDIT',
            'paid_amount': 0.0,
            'discount': 0.0,
            'tax': 0.0,
        }
        sale_id2 = sale_service.create_sale(sale_data, [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': 2000.0}], user_id=1)

        # Record payment 1: 1,500
        pay1 = credit_service.record_credit_payment(cust_id, {'amount': '1500.00', 'payment_method': 'UPI'}, user_id=1)

        # Record payment 2: 2,500
        pay2 = credit_service.record_credit_payment(cust_id, {'amount': '2500.00', 'payment_method': 'CASH'}, user_id=1)

        try:
            ledger = credit_service.get_customer_credit_history(cust_id)
            assert len(ledger) == 4

            # Verify running balances:
            # 1. Credit Sale 1 (+4000) -> 4000.00
            # 2. Credit Sale 2 (+2000) -> 6000.00
            # 3. Payment 1 (-1500)    -> 4500.00
            # 4. Payment 2 (-2500)    -> 2000.00
            assert ledger[0]['running_balance'] == Decimal('4000.00')
            assert ledger[1]['running_balance'] == Decimal('6000.00')
            assert ledger[2]['running_balance'] == Decimal('4500.00')
            assert ledger[3]['running_balance'] == Decimal('2000.00')

            # Final customer balance must equal last ledger entry
            final_bal = credit_service.get_customer_outstanding_balance(cust_id)
            assert final_bal == Decimal('2000.00')
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id1, sale_id2])


# ---------------------------------------------------------------------------
# 5. Settlement Payments Validation & Atomicity
# ---------------------------------------------------------------------------

def test_valid_settlement_payment_success(app):
    """21. Valid settlement payment creates payment & credit_transactions records."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(Decimal('5000.00'))
        try:
            res = credit_service.record_credit_payment(cust_id, {
                'amount': '3000.00',
                'payment_method': 'UPI',
                'reference_number': 'UPI-TEST-12345',
                'notes': 'Test payment'
            }, user_id=1)

            assert res['paid_amount'] == Decimal('3000.00')
            assert res['new_balance'] == Decimal('2000.00')

            # Verify payment row
            pay_row = query_db("SELECT * FROM payments WHERE payment_id = %s", (res['payment_id'],), one=True)
            assert pay_row is not None
            assert Decimal(str(pay_row['amount'])) == Decimal('3000.00')
            assert pay_row['payment_method'] == 'UPI'

            # Verify credit transaction row
            tx_row = query_db("SELECT * FROM credit_transactions WHERE transaction_id = %s", (res['transaction_id'],), one=True)
            assert tx_row is not None
            assert tx_row['transaction_type'] == 'PAYMENT'
            assert Decimal(str(tx_row['running_balance'])) == Decimal('2000.00')
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_settlement_zero_and_negative_payment_rejected(app):
    """22, 23. Zero and negative settlement amounts rejected."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('5000.00'))
        try:
            with pytest.raises(ValidationError, match="greater than zero"):
                credit_service.record_credit_payment(cust_id, {'amount': '0.00'}, user_id=1)

            with pytest.raises(ValidationError, match="greater than zero"):
                credit_service.record_credit_payment(cust_id, {'amount': '-500.00'}, user_id=1)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_settlement_greater_than_balance_rejected(app):
    """24. Payment greater than outstanding balance is rejected (prevent overpayment)."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3000.00'))
        try:
            with pytest.raises(ValidationError, match="cannot exceed customer's outstanding balance"):
                credit_service.record_credit_payment(cust_id, {'amount': '3000.01'}, user_id=1)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_settlement_invalid_customer_rejected(app):
    """25. Invalid customer ID rejected."""
    with app.app_context():
        with pytest.raises(ValidationError, match="does not exist"):
            credit_service.record_credit_payment(9999999, {'amount': '100.00'}, user_id=1)


def test_settlement_invalid_payment_method_rejected(app):
    """26. Invalid payment method rejected."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3000.00'))
        try:
            with pytest.raises(ValidationError, match="Invalid payment method"):
                credit_service.record_credit_payment(cust_id, {
                    'amount': '1000.00',
                    'payment_method': 'CRYPTO'
                }, user_id=1)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_settlement_malformed_amount_rejected(app):
    """27. Malformed non-numeric amount rejected."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3000.00'))
        try:
            with pytest.raises(ValidationError, match="valid positive number"):
                credit_service.record_credit_payment(cust_id, {
                    'amount': 'abc_invalid'
                }, user_id=1)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_settlement_available_credit_increases_correctly(app):
    """28, 29. Balance decreases and available credit increases accurately after payment."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(
            credit_amount=Decimal('8000.00'),
            credit_limit=Decimal('25000.00')
        )
        try:
            prof1 = credit_service.get_customer_credit_profile(cust_id)
            assert prof1['outstanding_balance'] == Decimal('8000.00')
            assert prof1['available_credit'] == Decimal('17000.00')

            credit_service.record_credit_payment(cust_id, {'amount': '5000.00', 'payment_method': 'CASH'}, user_id=1)

            prof2 = credit_service.get_customer_credit_profile(cust_id)
            assert prof2['outstanding_balance'] == Decimal('3000.00')
            assert prof2['available_credit'] == Decimal('22000.00')
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


# ---------------------------------------------------------------------------
# 6. Web Routes & Role Access
# ---------------------------------------------------------------------------

def test_unauthenticated_web_credit_routes_redirect(client):
    """31. Unauthenticated web requests redirect to /login."""
    assert client.get('/credit').status_code == 302
    assert client.get('/credit/customer/1').status_code == 302
    assert client.get('/credit/customer/1/payment').status_code == 302


def test_staff_and_admin_web_credit_access(staff_client, admin_client, app):
    """32, 33. Staff and Admin can view credit directory, profiles, and record payments."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('4000.00'))
    try:
        # Directory
        res_dir = staff_client.get('/credit')
        assert res_dir.status_code == 200
        assert b'Credit' in res_dir.data

        # Profile & Ledger
        res_view = staff_client.get(f'/credit/customer/{cust_id}')
        assert res_view.status_code == 200
        assert b'Chronological Credit Ledger' in res_view.data

        # Payment Form (GET)
        res_pay_get = staff_client.get(f'/credit/customer/{cust_id}/payment')
        assert res_pay_get.status_code == 200
        assert b'Record Credit Settlement' in res_pay_get.data

        # Payment Submit (POST)
        res_pay_post = staff_client.post(f'/credit/customer/{cust_id}/payment', data={
            'amount': '1000.00',
            'payment_method': 'CASH',
            'payment_date': date.today().strftime('%Y-%m-%d'),
            'reference_number': 'STAFF-PAY-01'
        }, follow_redirects=True)
        assert res_pay_post.status_code == 200
        assert b'Settlement payment of' in res_pay_post.data
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


# ---------------------------------------------------------------------------
# 7. REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_get_credit_summary(client):
    """34. GET /api/credit/summary."""
    res = client.get('/api/credit/summary')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'total_credit_to_collect' in data['data']
    assert 'total_credit_customers' in data['data']


def test_api_get_credit_customers(client):
    """35. GET /api/credit/customers."""
    res = client.get('/api/credit/customers')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert isinstance(data['data'], list)


def test_api_get_customer_credit_profile(client, app):
    """36. GET /api/credit/customer/<id>."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(Decimal('3500.00'))
    try:
        res = client.get(f'/api/credit/customer/{cust_id}')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert data['data']['outstanding_balance'] == float(amt)
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_api_get_customer_credit_profile_not_found(client):
    """37. GET /api/credit/customer/999999 returns 404."""
    res = client.get('/api/credit/customer/999999')
    assert res.status_code == 404
    assert res.get_json()['status'] == 'error'


def test_api_get_customer_credit_history(client, app):
    """38. GET /api/credit/customer/<id>/history."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3500.00'))
    try:
        res = client.get(f'/api/credit/customer/{cust_id}/history')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert data['count'] >= 1
        assert 'ledger' in data
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_api_record_credit_payment_success(admin_client, app):
    """39. POST /api/credit/customer/<id>/payment."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('5000.00'))
    try:
        res = admin_client.post(f'/api/credit/customer/{cust_id}/payment', json={
            'amount': 2000.0,
            'payment_method': 'UPI',
            'reference_number': 'API-REF-9988'
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data['status'] == 'success'
        assert data['data']['paid_amount'] == 2000.0
        assert data['data']['new_balance'] == 3000.0
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_api_record_credit_payment_overpayment_rejected(admin_client, app):
    """40. POST /api/credit/customer/<id>/payment overpayment returns 400."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('2000.00'))
    try:
        res = admin_client.post(f'/api/credit/customer/{cust_id}/payment', json={
            'amount': 2500.0,
            'payment_method': 'CASH'
        })
        assert res.status_code == 400
        assert 'cannot exceed' in res.get_json()['message']
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_api_record_credit_payment_unauthenticated(client, app):
    """41. POST /api/credit/customer/<id>/payment without auth or user_id rejected with 401."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('2000.00'))
    try:
        res = client.post(f'/api/credit/customer/{cust_id}/payment', json={
            'amount': 1000.0,
            'payment_method': 'CASH'
        })
        assert res.status_code == 401
    finally:
        with app.app_context():
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


# ---------------------------------------------------------------------------
# 8. Integration: POS Credit Sale + Settlement Flow & Dashboard Agreement
# ---------------------------------------------------------------------------

def test_pos_credit_sale_and_settlement_flow_integration(app):
    """35. Full End-to-End Cycle: Customer -> POS Credit Sale -> Balance up -> Settlement -> Balance down."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'EndToEndCreditCustomer',
            'phone': phone,
            'credit_limit': 30000.0,
            'status': 'ACTIVE'
        })

        # Step 1: Active customer in POS search has 0 balance
        pos_custs = customer_service.get_active_customers(search=phone)
        assert len(pos_custs) == 1
        assert to_decimal(pos_custs[0]['current_balance']) == Decimal('0.00')

        # Step 2: Make credit sale in POS
        variants = sale_service.get_active_variants_for_sale()
        var = variants[0]
        price = Decimal(str(var['selling_price']))
        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'payment_method': 'CREDIT',
            'paid_amount': 0.0,
            'discount': 0.0,
            'tax': 0.0,
        }
        sale_id = sale_service.create_sale(sale_data, [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': float(price)}], user_id=1)

        try:
            # Step 3: Outstanding balance increased to price
            bal1 = credit_service.get_customer_outstanding_balance(cust_id)
            assert bal1 == price

            # Step 4: Record settlement payment
            settle_amount = Decimal('500.00') if price > Decimal('500.00') else price
            pay_res = credit_service.record_credit_payment(cust_id, {
                'amount': str(settle_amount),
                'payment_method': 'UPI'
            }, user_id=1)

            # Step 5: Balance reduced
            bal2 = credit_service.get_customer_outstanding_balance(cust_id)
            assert bal2 == price - settle_amount

            # Step 6: Available credit in profile is credit_limit - new balance
            prof = credit_service.get_customer_credit_profile(cust_id)
            assert prof['available_credit'] == Decimal('30000.00') - (price - settle_amount)
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_dashboard_credit_total_matches_credit_summary(client):
    """36. Dashboard API total_credit_to_collect strictly equals /api/credit/summary total."""
    dash_res = client.get('/api/dashboard/summary')
    credit_res = client.get('/api/credit/summary')

    assert dash_res.status_code == 200
    assert credit_res.status_code == 200

    dash_total = dash_res.get_json()['data']['total_credit_to_collect']
    credit_total = credit_res.get_json()['data']['total_credit_to_collect']

    assert dash_total == credit_total


def test_credit_customers_min_balance_filter(app):
    """37. Directory filter by min_balance excludes customers with lower balance."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('3000.00'))
        try:
            high_bal = credit_service.get_credit_customers(min_balance=Decimal('5000.00'))
            matching_high = [c for c in high_bal if c['customer_id'] == cust_id]
            assert len(matching_high) == 0

            low_bal = credit_service.get_credit_customers(min_balance=Decimal('2000.00'))
            matching_low = [c for c in low_bal if c['customer_id'] == cust_id]
            assert len(matching_low) == 1
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_customer_profile_financials_match_credit_profile(app):
    """38. Credit profile invariant: outstanding + available_credit == credit_limit when outstanding < credit_limit."""
    with app.app_context():
        cust_id, sale_id, amt = create_test_customer_with_credit(
            credit_amount=Decimal('4500.00'),
            credit_limit=Decimal('25000.00')
        )
        try:
            prof = credit_service.get_customer_credit_profile(cust_id)

            outstanding = prof['outstanding_balance']
            available = prof['available_credit']
            limit = prof['credit_limit']

            # Core invariant: outstanding + available == credit_limit
            assert outstanding + available == limit, (
                f"Financial invariant broken: outstanding({outstanding}) + available({available}) != limit({limit})"
            )

            # Outstanding must equal the test credit amount
            assert outstanding == amt

            # Available = limit - outstanding
            assert available == limit - outstanding
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])



def test_credit_payment_notes_and_reference_recorded(app):
    """39. Reference number and notes are preserved in both payments and credit_transactions."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('6000.00'))
        try:
            res = credit_service.record_credit_payment(cust_id, {
                'amount': '2500.00',
                'payment_method': 'BANK_TRANSFER',
                'reference_number': 'NEFT-2026-987654',
                'notes': 'Partial NEFT clearance settlement'
            }, user_id=1)

            # Check payment table
            pay = query_db("SELECT reference_number, notes FROM payments WHERE payment_id = %s", (res['payment_id'],), one=True)
            assert pay['reference_number'] == 'NEFT-2026-987654'
            assert pay['notes'] == 'Partial NEFT clearance settlement'

            # Check credit_transactions table
            tx = query_db("SELECT notes FROM credit_transactions WHERE transaction_id = %s", (res['transaction_id'],), one=True)
            assert 'Partial NEFT clearance settlement' in tx['notes']
            assert 'NEFT-2026-987654' in tx['notes']
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_same_date_transaction_deterministic_ordering(app):
    """40. Transactions on same date order deterministically by transaction_id."""
    with app.app_context():
        cust_id, sale_id, _ = create_test_customer_with_credit(Decimal('5000.00'))
        try:
            # Add 2 payments on same day
            pay1 = credit_service.record_credit_payment(cust_id, {'amount': '1000.00', 'payment_method': 'CASH'}, user_id=1)
            pay2 = credit_service.record_credit_payment(cust_id, {'amount': '1000.00', 'payment_method': 'UPI'}, user_id=1)

            history = credit_service.get_customer_credit_history(cust_id)
            assert len(history) == 3
            # Transaction IDs must strictly increase
            tx_ids = [tx['transaction_id'] for tx in history]
            assert tx_ids == sorted(tx_ids)
            assert history[0]['running_balance'] == Decimal('5000.00')
            assert history[1]['running_balance'] == Decimal('4000.00')
            assert history[2]['running_balance'] == Decimal('3000.00')
        finally:
            cleanup_test_records(customer_ids=[cust_id], sale_ids=[sale_id])

