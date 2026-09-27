import pytest
from backend.app import create_app
from backend.utils.database import get_db_connection, query_db

@pytest.fixture
def app():
    """Create and configure a new app instance for tests."""
    app = create_app('testing')
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_app_creation(app):
    """Test Flask application startup and configuration."""
    assert app is not None
    assert app.config['BRAND_NAME'] == 'VL Silks'
    assert app.config['BRAND_PRIMARY_COLOR'] == '#8B0000'

def test_api_health_endpoint(client):
    """Test GET /api/health returns 200 and expected JSON payload."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'
    assert data['service'] == 'VL Silks'
    assert data['database'] == 'connected'

def test_database_connection():
    """Test MySQL database connection and cursor query."""
    conn = get_db_connection()
    assert conn.is_connected()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 AS test")
    result = cursor.fetchone()
    assert result[0] == 1
    cursor.close()
    conn.close()

def test_all_fifteen_tables_exist():
    """Verify that all 15 required database tables exist in vl_silks_db."""
    expected_tables = {
        'users',
        'categories',
        'products',
        'product_variants',
        'suppliers',
        'purchases',
        'purchase_items',
        'customers',
        'sales',
        'sale_items',
        'payments',
        'credit_transactions',
        'stock_movements',
        'returns',
        'return_items'
    }
    
    rows = query_db("SHOW TABLES")
    actual_tables = {list(row.values())[0] for row in rows}
    
    missing_tables = expected_tables - actual_tables
    assert not missing_tables, f"Missing tables: {missing_tables}"

def test_seed_data_integrity():
    """Verify that users, categories, products, variants, and customers are seeded."""
    users = query_db("SELECT user_id, email, role FROM users")
    assert len(users) >= 2
    emails = [u['email'] for u in users]
    assert 'admin@vlsilks.com' in emails
    assert 'staff@vlsilks.com' in emails

    categories = query_db("SELECT COUNT(*) AS cnt FROM categories")
    assert categories[0]['cnt'] >= 7

    variants = query_db("SELECT COUNT(*) AS cnt FROM product_variants")
    assert variants[0]['cnt'] >= 20

    customers = query_db("SELECT COUNT(*) AS cnt FROM customers")
    assert customers[0]['cnt'] >= 5

def test_login_flow(client):
    """Test web login flow with seeded credentials."""
    # GET Login page
    res = client.get('/login')
    assert res.status_code == 200
    assert b'Staff &amp; Admin Login' in res.data or b'Staff & Admin Login' in res.data

    # POST Valid Login
    res_post = client.post('/login', data={
        'email': 'admin@vlsilks.com',
        'password': 'Admin@123'
    }, follow_redirects=True)
    assert res_post.status_code == 200
    assert b'Shop Performance Dashboard' in res_post.data

def test_dashboard_credit_calculation():
    """Verify that total credit to collect is positive (seed + any test data)."""
    row = query_db("""
        SELECT COALESCE(SUM(CASE 
            WHEN transaction_type = 'CREDIT_SALE' THEN amount 
            WHEN transaction_type = 'PAYMENT' THEN -amount 
            WHEN transaction_type = 'RETURN_REFUND' THEN -amount 
            ELSE 0 
        END), 0) AS total_credit
        FROM credit_transactions
    """, one=True)

    # Seed data creates credit sales; test runs may add more.
    # Assert the running total is positive (seed guarantees this).
    assert float(row['total_credit']) > 0
