"""
VL Silks – Phase 12 Credit / Udhaar PDF Statement Test Suite
Comprehensive automated test suite covering ReportLab PDF generation, HTTP endpoints,
parameter validations, financial invariants, and multi-page pagination.
"""

import time
from decimal import Decimal
from datetime import date, datetime
import pytest
from flask import session

from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import credit_service, customer_service, sale_service, pdf_service
from backend.services.credit_service import ValidationError, to_decimal

_phone_counter = 500


def unique_phone():
    """Generate isolated unique phone numbers for test records."""
    global _phone_counter
    _phone_counter += 1
    t = int(time.time() * 1000) % 1000000
    return f"91{t:06d}{_phone_counter:02d}"


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


def cleanup_pdf_test_records(customer_ids=None, sale_ids=None):
    """Helper to restore stock and clean up test records safely."""
    with get_db_cursor(commit=True) as cursor:
        if sale_ids:
            format_s = ','.join(['%s'] * len(sale_ids))
            # Restore stock quantity before deleting sale_items
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
# 1. HTTP Endpoint Authentication & Access Control
# ---------------------------------------------------------------------------

def test_credit_pdf_endpoint_requires_auth(client):
    """1. GET /api/pdf/credit/:id requires active user authentication."""
    response = client.get('/api/pdf/credit/1')
    assert response.status_code == 401
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'Authentication required' in data['message']


def test_credit_pdf_endpoint_staff_access(staff_client):
    """2. Staff user can generate and download customer credit PDF."""
    response = staff_client.get('/api/pdf/credit/1')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert response.data.startswith(b'%PDF')


def test_credit_pdf_endpoint_admin_access(admin_client):
    """3. Admin user can generate and download customer credit PDF."""
    response = admin_client.get('/api/pdf/credit/1')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert response.data.startswith(b'%PDF')


# ---------------------------------------------------------------------------
# 2. PDF Response Headers & Content Validation
# ---------------------------------------------------------------------------

def test_credit_pdf_headers_and_disposition(admin_client):
    """4. PDF response contains appropriate headers, cache controls, and meaningful filename."""
    response = admin_client.get('/api/pdf/credit/1')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert 'attachment;' in response.headers['Content-Disposition']
    assert 'filename="VL-Silks-Credit-Statement-' in response.headers['Content-Disposition']
    assert '.pdf"' in response.headers['Content-Disposition']
    assert response.headers['Cache-Control'] == 'no-cache, no-store, must-revalidate'


def test_credit_pdf_valid_magic_bytes(admin_client):
    """5. Generated PDF stream begins with valid %PDF magic header and has substantial size."""
    response = admin_client.get('/api/pdf/credit/1')
    assert response.status_code == 200
    assert response.data.startswith(b'%PDF')
    assert len(response.data) > 1000  # Non-empty, properly structured PDF


# ---------------------------------------------------------------------------
# 3. Parameter Validation & Error Handling (404, 400)
# ---------------------------------------------------------------------------

def test_credit_pdf_nonexistent_customer_returns_404(admin_client):
    """6. Non-existent customer ID returns 404 Not Found."""
    response = admin_client.get('/api/pdf/credit/999999')
    assert response.status_code == 404
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'not found' in data['message'].lower()


def test_credit_pdf_invalid_date_from_returns_400(admin_client):
    """7. Invalid date_from format returns 400 Bad Request."""
    response = admin_client.get('/api/pdf/credit/1?date_from=25-09-2026')
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'Invalid date_from' in data['message']


def test_credit_pdf_invalid_date_to_returns_400(admin_client):
    """8. Invalid date_to format returns 400 Bad Request."""
    response = admin_client.get('/api/pdf/credit/1?date_to=invalid-date')
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'Invalid date_to' in data['message']


def test_credit_pdf_date_from_after_date_to_returns_400(admin_client):
    """9. date_from later than date_to returns 400 Bad Request."""
    response = admin_client.get('/api/pdf/credit/1?date_from=2026-09-25&date_to=2026-09-01')
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert 'cannot be later than' in data['message']


# ---------------------------------------------------------------------------
# 4. Statement Period Filtering
# ---------------------------------------------------------------------------

def test_credit_pdf_date_filtered_statement(admin_client):
    """10. Valid date_from and date_to parameters successfully generate period-filtered statement."""
    response = admin_client.get('/api/pdf/credit/1?date_from=2026-09-01&date_to=2026-09-30')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    disposition = response.headers['Content-Disposition']
    assert '20260901-20260930.pdf' in disposition


def test_credit_pdf_date_from_only_statement(admin_client):
    """11. Statement with only date_from generates valid PDF."""
    response = admin_client.get('/api/pdf/credit/1?date_from=2026-09-01')
    assert response.status_code == 200
    assert response.data.startswith(b'%PDF')


def test_credit_pdf_date_to_only_statement(admin_client):
    """12. Statement with only date_to generates valid PDF."""
    response = admin_client.get('/api/pdf/credit/1?date_to=2026-09-30')
    assert response.status_code == 200
    assert response.data.startswith(b'%PDF')


# ---------------------------------------------------------------------------
# 5. Service Layer & Lifecycle Tests
# ---------------------------------------------------------------------------

def test_credit_pdf_service_customer_with_no_history(app):
    """13. Customer with 0 transactions generates clean PDF with empty-state notice."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'ZeroCreditHistoryCust',
            'phone': phone,
            'credit_limit': 15000.0,
            'status': 'ACTIVE'
        })
        try:
            pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(cust_id)
            assert pdf_bytes.startswith(b'%PDF')
            assert 'ZeroCreditHistoryCust' in filename
            assert len(pdf_bytes) > 1000
        finally:
            cleanup_pdf_test_records(customer_ids=[cust_id])


def test_credit_pdf_service_inactive_customer(app):
    """14. Inactive customer with credit history can still have PDF generated."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'InactiveCreditCust',
            'phone': phone,
            'credit_limit': 20000.0,
            'status': 'ACTIVE'
        })
        # Make a sale
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
        sale_id = sale_service.create_sale(sale_data, [{'variant_id': var['variant_id'], 'quantity': 1, 'unit_price': 5000.0}], user_id=1)

        # Deactivate customer
        customer_service.toggle_customer_status(cust_id)
        cust_prof = credit_service.get_customer_credit_profile(cust_id)
        assert cust_prof['status'] == 'INACTIVE'

        try:
            pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(cust_id)
            assert pdf_bytes.startswith(b'%PDF')
            assert 'InactiveCreditCust' in filename
        finally:
            cleanup_pdf_test_records(customer_ids=[cust_id], sale_ids=[sale_id])


def test_credit_pdf_service_logo_fallback(app, monkeypatch):
    """15. PDF generation succeeds even if logo image cannot be loaded."""
    with app.app_context():
        # Monkeypatch get_logo_image_path to return None
        monkeypatch.setattr(pdf_service, 'get_logo_image_path', lambda: None)
        pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(1)
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000


def test_credit_pdf_multi_page_ledger(app):
    """16. Customer with a large number of transactions generates multi-page PDF without errors."""
    with app.app_context():
        phone = unique_phone()
        cust_id = customer_service.create_customer({
            'customer_name': 'MultiPageStatementCust',
            'phone': phone,
            'credit_limit': 100000.0,
            'status': 'ACTIVE'
        })

        # Insert 35 simulated credit transactions directly to test pagination
        with get_db_cursor(commit=True) as cursor:
            for i in range(1, 36):
                t_type = 'CREDIT_SALE' if i % 2 != 0 else 'PAYMENT'
                amt = Decimal('1000.00')
                cursor.execute("""
                    INSERT INTO credit_transactions 
                    (customer_id, transaction_type, amount, transaction_date, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (cust_id, t_type, amt, f'2026-08-{i%28 + 1:02d}', f'Pagination ledger entry #{i}', 1))

        try:
            pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(cust_id)
            assert pdf_bytes.startswith(b'%PDF')
            assert len(pdf_bytes) > 2000
        finally:
            cleanup_pdf_test_records(customer_ids=[cust_id])


# ---------------------------------------------------------------------------
# 6. Financial Integrity: Read-Only Verification
# ---------------------------------------------------------------------------

def test_credit_pdf_generation_is_read_only_and_idempotent(app, admin_client):
    """17. PDF generation MUST be strictly read-only and not alter any financial state."""
    with app.app_context():
        prof_before = credit_service.get_customer_credit_profile(1)
        bal_before = prof_before['outstanding_balance']
        history_len_before = len(credit_service.get_customer_credit_history(1))
        
        tx_count_before = query_db("SELECT COUNT(*) as cnt FROM credit_transactions", one=True)['cnt']
        sales_count_before = query_db("SELECT COUNT(*) as cnt FROM sales", one=True)['cnt']
        payments_count_before = query_db("SELECT COUNT(*) as cnt FROM payments", one=True)['cnt']

    # Generate PDF 3 consecutive times
    for _ in range(3):
        res = admin_client.get('/api/pdf/credit/1')
        assert res.status_code == 200

    with app.app_context():
        prof_after = credit_service.get_customer_credit_profile(1)
        bal_after = prof_after['outstanding_balance']
        history_len_after = len(credit_service.get_customer_credit_history(1))
        
        tx_count_after = query_db("SELECT COUNT(*) as cnt FROM credit_transactions", one=True)['cnt']
        sales_count_after = query_db("SELECT COUNT(*) as cnt FROM sales", one=True)['cnt']
        payments_count_after = query_db("SELECT COUNT(*) as cnt FROM payments", one=True)['cnt']

        assert bal_before == bal_after
        assert history_len_before == history_len_after
        assert tx_count_before == tx_count_after
        assert sales_count_before == sales_count_after
        assert payments_count_before == payments_count_after


# ---------------------------------------------------------------------------
# 7. Web Route Direct Downloads & Error Redirects
# ---------------------------------------------------------------------------

def test_web_download_credit_statement_unauthenticated(client):
    """18. Web route redirects unauthenticated user to login."""
    response = client.get('/credit/customer/1/statement')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_web_download_credit_statement_authenticated(staff_client):
    """19. Web route streams PDF directly for authenticated staff/admin."""
    response = staff_client.get('/credit/customer/1/statement')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert response.data.startswith(b'%PDF')


def test_web_download_credit_statement_nonexistent(admin_client):
    """20. Web route redirects with warning if customer does not exist."""
    response = admin_client.get('/credit/customer/999999/statement', follow_redirects=True)
    assert response.status_code == 200
    assert b'not found' in response.data


def test_web_download_credit_statement_invalid_date_redirect(admin_client):
    """21. Web route redirects with error flash if invalid date filter provided."""
    response = admin_client.get('/credit/customer/1/statement?date_from=2026-09-25&date_to=2026-09-01', follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid statement period' in response.data
