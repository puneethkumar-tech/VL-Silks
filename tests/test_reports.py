"""
VL Silks - Phase 15 Reports Tests
Tests for all 5 report types: Sales, Purchase, Inventory Valuation,
Credit Aging, and Profit. Covers routes, API endpoints, CSV export,
and service-layer business logic.
"""
import pytest
from backend.app import create_app
from backend.services import report_service


@pytest.fixture
def app():
    return create_app('testing')


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Admin'
        sess['user_role'] = 'ADMIN'
    return client


# -----------------------------------------------------------------------
# REPORTS INDEX
# -----------------------------------------------------------------------

def test_reports_index_requires_auth(client):
    res = client.get('/reports', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location


def test_reports_index_renders(auth_client):
    res = auth_client.get('/reports')
    assert res.status_code == 200
    assert b'VL Silks Reports' in res.data
    assert b'Sales Report' in res.data
    assert b'Purchase Report' in res.data
    assert b'Inventory Valuation' in res.data
    assert b'Credit' in res.data
    assert b'Profit Report' in res.data


# -----------------------------------------------------------------------
# SALES REPORT
# -----------------------------------------------------------------------

def test_sales_report_page_requires_auth(client):
    res = client.get('/reports/sales', follow_redirects=False)
    assert res.status_code == 302


def test_sales_report_page_renders(auth_client):
    res = auth_client.get('/reports/sales')
    assert res.status_code == 200
    assert b'Sales' in res.data


def test_sales_report_page_with_date_filter(auth_client):
    res = auth_client.get('/reports/sales?start_date=2024-01-01&end_date=2030-12-31')
    assert res.status_code == 200


def test_api_sales_report_success(client):
    res = client.get('/api/reports/sales')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    r = data['data']
    assert 'sales' in r
    assert 'summary' in r
    assert 'payment_breakdown' in r
    sm = r['summary']
    assert 'invoice_count' in sm
    assert 'total_revenue' in sm
    assert 'total_paid' in sm
    assert 'total_credit' in sm
    assert 'total_units_sold' in sm
    assert isinstance(sm['invoice_count'], int)
    assert isinstance(sm['total_revenue'], float)


def test_api_sales_report_with_dates(client):
    res = client.get('/api/reports/sales?start_date=2024-01-01&end_date=2030-12-31')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['data']['start_date'] == '2024-01-01'
    assert data['data']['end_date'] == '2030-12-31'


def test_api_sales_csv_download(client):
    res = client.get('/api/reports/sales/csv')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type
    assert b'Invoice No.' in res.data or b'Invoice' in res.data


def test_sales_report_service_structure():
    data = report_service.get_sales_report()
    assert isinstance(data, dict)
    assert 'sales' in data
    assert 'summary' in data
    assert 'payment_breakdown' in data
    assert isinstance(data['sales'], list)
    sm = data['summary']
    assert sm['invoice_count'] >= 0
    assert sm['total_revenue'] >= 0
    assert sm['total_paid'] >= 0
    assert sm['total_credit'] >= 0


def test_sales_csv_bytes():
    csv_bytes = report_service.export_sales_report_csv()
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0
    text = csv_bytes.decode('utf-8-sig')
    assert 'Invoice No.' in text or 'TOTAL' in text


# -----------------------------------------------------------------------
# PURCHASE REPORT
# -----------------------------------------------------------------------

def test_purchase_report_page_requires_auth(client):
    res = client.get('/reports/purchases', follow_redirects=False)
    assert res.status_code == 302


def test_purchase_report_page_renders(auth_client):
    res = auth_client.get('/reports/purchases')
    assert res.status_code == 200
    assert b'Purchase' in res.data


def test_api_purchase_report_success(client):
    res = client.get('/api/reports/purchases')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    r = data['data']
    assert 'purchases' in r
    assert 'summary' in r
    assert 'supplier_breakdown' in r
    sm = r['summary']
    assert 'bill_count' in sm
    assert 'total_cost' in sm
    assert 'total_paid' in sm
    assert 'total_due' in sm


def test_api_purchase_csv_download(client):
    res = client.get('/api/reports/purchases/csv')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type


def test_purchase_report_service_structure():
    data = report_service.get_purchase_report()
    assert isinstance(data, dict)
    sm = data['summary']
    assert sm['bill_count'] >= 0
    assert sm['total_cost'] >= 0
    assert sm['total_paid'] >= 0
    assert sm['total_due'] >= 0


def test_purchase_csv_bytes():
    csv_bytes = report_service.export_purchase_report_csv()
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0


# -----------------------------------------------------------------------
# INVENTORY VALUATION
# -----------------------------------------------------------------------

def test_inventory_valuation_page_requires_auth(client):
    res = client.get('/reports/inventory-valuation', follow_redirects=False)
    assert res.status_code == 302


def test_inventory_valuation_page_renders(auth_client):
    res = auth_client.get('/reports/inventory-valuation')
    assert res.status_code == 200
    assert b'Inventory' in res.data


def test_api_inventory_valuation_success(client):
    res = client.get('/api/reports/inventory-valuation')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    r = data['data']
    assert 'variants' in r
    assert 'summary' in r
    assert 'category_subtotals' in r
    sm = r['summary']
    assert 'total_variants' in sm
    assert 'total_units' in sm
    assert 'total_cost_value' in sm
    assert 'total_selling_value' in sm
    assert 'total_potential_margin' in sm
    assert 'low_stock_count' in sm
    assert sm['total_variants'] >= 0
    assert sm['total_cost_value'] >= 0


def test_api_inventory_valuation_csv(client):
    res = client.get('/api/reports/inventory-valuation/csv')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type


def test_inventory_valuation_service_structure():
    data = report_service.get_inventory_valuation_report()
    assert isinstance(data, dict)
    assert 'variants' in data
    assert 'generated_at' in data
    sm = data['summary']
    assert sm['total_cost_value'] >= 0
    assert sm['total_selling_value'] >= sm['total_cost_value'] or sm['total_selling_value'] >= 0


def test_inventory_valuation_variant_fields():
    data = report_service.get_inventory_valuation_report()
    for v in data['variants']:
        assert 'variant_id' in v
        assert 'product_name' in v
        assert 'sku' in v
        assert 'stock_quantity' in v
        assert 'purchase_price' in v
        assert 'selling_price' in v
        assert 'stock_value_at_cost' in v
        assert 'stock_value_at_selling' in v
        assert 'potential_margin' in v
        assert 'is_low_stock' in v
        assert isinstance(v['is_low_stock'], bool)
        # Low stock flag consistency
        assert v['is_low_stock'] == (v['stock_quantity'] <= v['minimum_stock'])


def test_inventory_valuation_csv_bytes():
    csv_bytes = report_service.export_inventory_valuation_csv()
    assert isinstance(csv_bytes, bytes)
    text = csv_bytes.decode('utf-8-sig')
    assert 'Category' in text


# -----------------------------------------------------------------------
# CREDIT AGING REPORT
# -----------------------------------------------------------------------

def test_credit_aging_page_requires_auth(client):
    res = client.get('/reports/credit-aging', follow_redirects=False)
    assert res.status_code == 302


def test_credit_aging_page_renders(auth_client):
    res = auth_client.get('/reports/credit-aging')
    assert res.status_code == 200
    assert b'Credit' in res.data or b'Udhaar' in res.data


def test_api_credit_aging_success(client):
    res = client.get('/api/reports/credit-aging')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    r = data['data']
    assert 'customers' in r
    assert 'buckets' in r
    assert 'summary' in r
    sm = r['summary']
    assert 'customer_count' in sm
    assert 'total_outstanding' in sm
    assert '0_30_days' in sm
    assert '31_60_days' in sm
    assert '61_90_days' in sm
    assert '91_plus_days' in sm


def test_api_credit_aging_csv(client):
    res = client.get('/api/reports/credit-aging/csv')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type


def test_credit_aging_service_structure():
    data = report_service.get_credit_aging_report()
    assert isinstance(data, dict)
    sm = data['summary']
    assert sm['total_outstanding'] >= 0
    # Bucket totals must sum to total
    bucket_total = (sm['0_30_days'] + sm['31_60_days'] +
                    sm['61_90_days'] + sm['91_plus_days'])
    assert abs(bucket_total - sm['total_outstanding']) < 0.02


def test_credit_aging_customer_fields():
    data = report_service.get_credit_aging_report()
    for c in data['customers']:
        assert 'customer_id' in c
        assert 'customer_name' in c
        assert 'outstanding_balance' in c
        assert c['outstanding_balance'] > 0
        assert 'bucket' in c
        assert c['bucket'] in ('0_30', '31_60', '61_90', '91_plus')
        assert 'age_days' in c
        assert c['age_days'] >= 0


def test_credit_aging_csv_bytes():
    csv_bytes = report_service.export_credit_aging_csv()
    assert isinstance(csv_bytes, bytes)
    text = csv_bytes.decode('utf-8-sig')
    assert 'Customer' in text


# -----------------------------------------------------------------------
# PROFIT REPORT
# -----------------------------------------------------------------------

def test_profit_report_page_requires_auth(client):
    res = client.get('/reports/profit', follow_redirects=False)
    assert res.status_code == 302


def test_profit_report_page_renders(auth_client):
    res = auth_client.get('/reports/profit')
    assert res.status_code == 200
    assert b'Profit' in res.data


def test_api_profit_report_success(client):
    res = client.get('/api/reports/profit')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    r = data['data']
    assert 'products' in r
    assert 'summary' in r
    sm = r['summary']
    assert 'product_count' in sm
    assert 'total_revenue' in sm
    assert 'total_cost' in sm
    assert 'gross_profit' in sm
    assert 'overall_margin_percent' in sm
    assert sm['product_count'] >= 0
    assert isinstance(sm['total_revenue'], float)


def test_api_profit_report_with_dates(client):
    res = client.get('/api/reports/profit?start_date=2024-01-01&end_date=2030-12-31')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'


def test_api_profit_csv(client):
    res = client.get('/api/reports/profit/csv')
    assert res.status_code == 200
    assert 'text/csv' in res.content_type


def test_profit_report_service_structure():
    data = report_service.get_profit_report()
    assert isinstance(data, dict)
    sm = data['summary']
    # gross_profit should be revenue minus cost (approximately)
    assert abs(sm['gross_profit'] - (sm['total_revenue'] - sm['total_cost'])) < 0.05


def test_profit_report_product_fields():
    data = report_service.get_profit_report()
    for p in data['products']:
        assert 'product_id' in p
        assert 'product_name' in p
        assert 'category_name' in p
        assert 'units_sold' in p
        assert 'total_revenue' in p
        assert 'total_cost' in p
        assert 'gross_profit' in p
        assert 'margin_percent' in p
        assert isinstance(p['margin_percent'], float)
        assert p['units_sold'] >= 0
        # Margin should be between -100 and 100 in normal cases (may differ on discounted sales)
        assert -200.0 <= p['margin_percent'] <= 200.0


def test_profit_csv_bytes():
    csv_bytes = report_service.export_profit_report_csv()
    assert isinstance(csv_bytes, bytes)
    text = csv_bytes.decode('utf-8-sig')
    assert 'Product Name' in text
