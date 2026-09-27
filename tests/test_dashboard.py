"""
VL Silks - Phase 14 Dashboard Tests
Comprehensive automated tests for Dashboard routes, APIs, and business service calculations.
"""
import pytest
from backend.app import create_app
from backend.services import dashboard_service


@pytest.fixture
def app():
    """Create and configure application for testing."""
    app = create_app('testing')
    yield app


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Authenticated staff/admin test client."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Admin User'
        sess['user_role'] = 'ADMIN'
    return client


def test_home_redirect_anonymous(client):
    """Home route redirects anonymous user to login."""
    res = client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location


def test_home_redirect_authenticated(auth_client):
    """Home route redirects authenticated user to dashboard."""
    res = auth_client.get('/', follow_redirects=False)
    assert res.status_code == 302
    assert '/dashboard' in res.location


def test_dashboard_view_requires_auth(client):
    """GET /dashboard without session redirects to login."""
    res = client.get('/dashboard', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location


def test_dashboard_view_renders_correctly(auth_client):
    """GET /dashboard renders main dashboard page with all components."""
    res = auth_client.get('/dashboard')
    assert res.status_code == 200
    assert b'Shop Performance Dashboard' in res.data
    assert b'Today\'s Sales' in res.data
    assert b'This Month\'s Sales' in res.data
    assert b'Total Stock in Shop' in res.data
    assert b'Credit / Udhaar to Collect' in res.data
    assert b'Monthly Sales &amp; Revenue Trend' in res.data or b'Monthly Sales & Revenue Trend' in res.data
    assert b'Category Sales' in res.data
    assert b'Recent Sales Transactions' in res.data
    assert b'Top Selling Garments' in res.data
    assert b'Low Stock Alerts' in res.data
    assert b'Quick Operations' in res.data
    assert b'monthlySalesChart' in res.data
    assert b'categoryDistributionChart' in res.data


def test_api_dashboard_summary(client):
    """GET /api/dashboard/summary returns structured metrics."""
    res = client.get('/api/dashboard/summary')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    data = json_data['data']

    expected_keys = [
        'total_products', 'total_categories', 'total_variants',
        'total_stock', 'low_stock_count', 'today_sales',
        'today_sales_count', 'month_sales', 'month_sales_count',
        'total_credit_to_collect', 'customers_with_credit'
    ]
    for key in expected_keys:
        assert key in data, f"Missing key '{key}' in summary"
        assert isinstance(data[key], (int, float))


def test_api_dashboard_recent_sales(client):
    """GET /api/dashboard/recent-sales returns recent transactions list."""
    res = client.get('/api/dashboard/recent-sales?limit=5')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    assert 'data' in json_data
    assert isinstance(json_data['data'], list)
    if json_data['data']:
        first = json_data['data'][0]
        assert 'sale_id' in first
        assert 'invoice_number' in first
        assert 'total_amount' in first
        assert 'payment_status' in first


def test_api_dashboard_low_stock(client):
    """GET /api/dashboard/low-stock returns variant inventory alerts."""
    res = client.get('/api/dashboard/low-stock?limit=10')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    assert 'data' in json_data
    assert isinstance(json_data['data'], list)
    for item in json_data['data']:
        assert 'variant_id' in item
        assert 'sku' in item
        assert 'stock_quantity' in item
        assert 'minimum_stock' in item
        assert item['stock_quantity'] <= item['minimum_stock']


def test_api_dashboard_monthly_sales(client):
    """GET /api/dashboard/monthly-sales returns 6-month aggregate chart data."""
    res = client.get('/api/dashboard/monthly-sales?months=6')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    data = json_data['data']
    assert 'labels' in data
    assert 'sales' in data
    assert 'paid' in data
    assert 'credit' in data
    assert 'counts' in data
    assert 'details' in data
    assert len(data['labels']) == 6
    assert len(data['sales']) == 6


def test_api_dashboard_top_products(client):
    """GET /api/dashboard/top-products returns top selling garments."""
    res = client.get('/api/dashboard/top-products?limit=5')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    assert 'data' in json_data
    assert isinstance(json_data['data'], list)
    if json_data['data']:
        top1 = json_data['data'][0]
        assert 'product_id' in top1
        assert 'product_name' in top1
        assert 'total_units_sold' in top1
        assert 'total_revenue' in top1


def test_api_dashboard_category_distribution(client):
    """GET /api/dashboard/category-distribution returns category sales breakdown."""
    res = client.get('/api/dashboard/category-distribution')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['status'] == 'success'
    data = json_data['data']
    assert 'categories' in data
    assert 'revenue' in data
    assert 'units' in data
    assert 'details' in data


def test_dashboard_service_summary_direct():
    """Unit test for dashboard_service.get_dashboard_summary."""
    summary = dashboard_service.get_dashboard_summary()
    assert isinstance(summary, dict)
    assert summary['total_products'] >= 0
    assert summary['total_variants'] >= 0
    assert summary['total_stock'] >= 0
    assert summary['today_sales'] >= 0
    assert summary['today_returns_amount'] >= 0
    assert summary['today_net_sales'] == summary['today_sales'] - summary['today_returns_amount']
    assert summary['month_net_sales'] == summary['month_sales'] - summary['month_returns_amount']


def test_dashboard_service_monthly_sales_12_months():
    """Unit test for monthly sales with custom 12-month interval."""
    res = dashboard_service.get_monthly_sales(months=12)
    assert len(res['labels']) == 12
    assert len(res['sales']) == 12
    assert len(res['details']) == 12
    for d in res['details']:
        assert 'month_key' in d
        assert 'total_sales' in d
        assert 'invoice_count' in d
