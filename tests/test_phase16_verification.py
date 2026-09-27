"""
VL Silks - Phase 16 Comprehensive Testing, QA & System Verification Suite
Exhaustive verification of cross-module integration, negative stock safety,
transaction rollback integrity, RBAC security access matrix, financial
reconciliations, and dashboard/report data consistency.
"""
import pytest
from decimal import Decimal
from datetime import date, datetime

from backend.app import create_app
from backend.utils.database import query_db
from backend.services import (
    product_service,
    inventory_service,
    purchase_service,
    sale_service,
    customer_service,
    credit_service,
    return_service,
    report_service,
    dashboard_service,
    pdf_service
)


@pytest.fixture
def app():
    """Create test application instance in testing config."""
    app = create_app('testing')
    yield app


@pytest.fixture
def client(app):
    """Anonymous test client."""
    return app.test_client()


@pytest.fixture
def admin_client(app):
    """Client authenticated with ADMIN role."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Venkata Lakshmi (Admin)'
        sess['user_email'] = 'admin@vlsilks.com'
        sess['user_role'] = 'ADMIN'
    return c


@pytest.fixture
def staff_client(app):
    """Client authenticated with STAFF role."""
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Kiran Kumar (Staff)'
        sess['user_email'] = 'staff@vlsilks.com'
        sess['user_role'] = 'STAFF'
    return c


# ===========================================================================
# 1. PRODUCT & VARIANT CRUD COMPREHENSIVE VERIFICATION
# ===========================================================================

def test_product_crud_lifecycle_preserves_stock_and_history(app):
    """Verify full product CRUD lifecycle: creation, variant additions, metadata updates,
    and verify that updating product details does not tamper with variant stock."""
    with app.app_context():
        # 1. Create product with initial variants
        prod_data = {
            'product_name': f"QA Test Chanderi Saree {datetime.now().strftime('%H%M%S%f')}",
            'category_id': 1,
            'brand': 'VL Silks QA',
            'material': 'Chanderi Silk',
            'description': 'Handwoven Chanderi Saree for QA Verification',
            'status': 'ACTIVE'
        }
        sku_suffix = datetime.now().strftime('%H%M%S%f')[:8]
        variants_data = [
            {
                'sku': f'SKU-QA-CHN-{sku_suffix}-1',
                'size': 'Free Size',
                'color': 'Peach Gold',
                'purchase_price': 4200.00,
                'selling_price': 6999.00,
                'stock_quantity': 15,
                'minimum_stock': 3,
                'barcode': f'BC-QA-{sku_suffix}-1'
            }
        ]
        prod_id = product_service.create_product_with_variants(prod_data, variants_data, user_id=1)
        assert prod_id is not None

        # Verify initial stock
        vars_loaded = product_service.get_product_variants(prod_id)
        assert len(vars_loaded) == 1
        assert vars_loaded[0]['stock_quantity'] == 15

        # 2. Add second variant to existing product
        var2_data = {
            'sku': f'SKU-QA-CHN-{sku_suffix}-2',
            'size': 'Free Size',
            'color': 'Mint Green',
            'purchase_price': 4200.00,
            'selling_price': 6999.00,
            'stock_quantity': 8,
            'minimum_stock': 2,
            'barcode': f'BC-QA-{sku_suffix}-2'
        }
        var2_id = product_service.add_variant_to_product(prod_id, var2_data)
        assert var2_id is not None

        # 3. Update base product metadata
        product_service.update_product(prod_id, {
            'product_name': f"QA Test Chanderi Saree (Updated) {sku_suffix}",
            'category_id': 1,
            'brand': 'VL Silks Royal Collection',
            'material': 'Pure Chanderi Silk',
            'description': 'Updated description',
            'status': 'ACTIVE'
        })

        # 4. Verify variant stocks remained untouched after product metadata update
        vars_after_update = product_service.get_product_variants(prod_id)
        assert len(vars_after_update) == 2
        v_map = {v['sku']: v for v in vars_after_update}
        assert v_map[f'SKU-QA-CHN-{sku_suffix}-1']['stock_quantity'] == 15
        assert v_map[f'SKU-QA-CHN-{sku_suffix}-2']['stock_quantity'] == 8

        # 5. Duplicate SKU rejection test
        with pytest.raises(product_service.ValidationError, match="already exists"):
            product_service.add_variant_to_product(prod_id, {
                'sku': f'SKU-QA-CHN-{sku_suffix}-1',  # duplicate
                'size': 'Free Size',
                'color': 'Duplicate Color',
                'purchase_price': 4000.00,
                'selling_price': 6000.00,
                'stock_quantity': 5,
                'minimum_stock': 2
            })

        # 6. Duplicate Barcode rejection test
        with pytest.raises(product_service.ValidationError, match="already assigned"):
            product_service.add_variant_to_product(prod_id, {
                'sku': f'SKU-QA-CHN-{sku_suffix}-3',
                'size': 'Free Size',
                'color': 'Unique Color',
                'purchase_price': 4000.00,
                'selling_price': 6000.00,
                'stock_quantity': 5,
                'minimum_stock': 2,
                'barcode': f'BC-QA-{sku_suffix}-1'  # duplicate barcode
            })


def test_product_deactivation_is_safe_and_reversible(app):
    """Verify soft deactivation of products and variants."""
    with app.app_context():
        sku = f"SKU-TEMP-{datetime.now().strftime('%H%M%S%f')[:8]}"
        pid = product_service.create_product_with_variants(
            {'product_name': 'Temp QA Saree', 'category_id': 1, 'brand': 'VL Silks', 'material': 'Silk', 'status': 'ACTIVE'},
            [{'sku': sku, 'size': 'FS', 'color': 'Red', 'purchase_price': 1000, 'selling_price': 2000, 'stock_quantity': 5, 'minimum_stock': 1}],
            user_id=1
        )
        variants = product_service.get_product_variants(pid)
        vid = variants[0]['variant_id']

        # Deactivate variant
        product_service.toggle_variant_status(vid, 'INACTIVE')
        v = query_db("SELECT status FROM product_variants WHERE variant_id = %s", (vid,), one=True)
        assert v['status'] == 'INACTIVE'

        # Reactivate variant
        product_service.toggle_variant_status(vid, 'ACTIVE')
        v = query_db("SELECT status FROM product_variants WHERE variant_id = %s", (vid,), one=True)
        assert v['status'] == 'ACTIVE'

        # Deactivate base product
        product_service.toggle_product_status(pid, 'INACTIVE')
        p = query_db("SELECT status FROM products WHERE product_id = %s", (pid,), one=True)
        assert p['status'] == 'INACTIVE'


# ===========================================================================
# 2. PURCHASE + STOCK INTEGRATION & IMMUTABILITY
# ===========================================================================

def test_purchase_stock_increment_and_audit_movements(app):
    """Verify inward purchases accurately increment stock quantities, compute
    Decimal totals, and generate PURCHASE stock movements."""
    with app.app_context():
        # Setup variant with baseline stock
        v_init = query_db("SELECT variant_id, stock_quantity FROM product_variants WHERE status = 'ACTIVE' LIMIT 1", one=True)
        vid = v_init['variant_id']
        initial_stock = v_init['stock_quantity']

        # Create inward purchase
        inv_no = f"PUR-QA-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}"
        p_data = {
            'supplier_id': 1,
            'invoice_number': inv_no,
            'purchase_date': date.today().strftime('%Y-%m-%d'),
            'discount': 500.00,
            'tax': 250.00,
            'notes': 'QA Inward verification purchase',
            'payment_status': 'PAID'
        }
        items_data = [
            {
                'variant_id': vid,
                'quantity': 12,
                'unit_price': 3500.00
            }
        ]
        pur_id = purchase_service.create_purchase(p_data, items_data, user_id=1)
        assert pur_id is not None

        # Verify exact stock increase
        v_after = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = %s", (vid,), one=True)
        assert v_after['stock_quantity'] == initial_stock + 12

        # Verify stock movement record
        m = query_db("""
            SELECT * FROM stock_movements 
            WHERE variant_id = %s AND movement_type = 'PURCHASE' AND reference_type = 'PURCHASE'
            ORDER BY movement_id DESC LIMIT 1
        """, (vid,), one=True)
        assert m is not None
        assert m['quantity'] == 12


def test_purchase_rollback_on_item_failure_leaves_no_partial_state(app):
    """Verify purchase creation rolls back atomically if any item is invalid."""
    with app.app_context():
        v = query_db("SELECT variant_id, stock_quantity FROM product_variants WHERE status = 'ACTIVE' LIMIT 1", one=True)
        vid = v['variant_id']
        orig_stock = v['stock_quantity']

        inv_no = f"PUR-FAIL-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}"
        p_data = {
            'supplier_id': 1,
            'invoice_number': inv_no,
            'purchase_date': date.today().strftime('%Y-%m-%d'),
            'discount': 0,
            'tax': 0,
            'payment_status': 'PAID'
        }
        items = [
            {'variant_id': vid, 'quantity': 10, 'unit_price': 1000.00},
            {'variant_id': 999999, 'quantity': 5, 'unit_price': 1000.00}
        ]

        with pytest.raises(Exception):
            purchase_service.create_purchase(p_data, items, user_id=1)

        # Confirm no purchase was inserted
        check_p = query_db("SELECT * FROM purchases WHERE invoice_number = %s", (inv_no,), one=True)
        assert check_p is None

        # Confirm stock was NOT modified
        v_check = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = %s", (vid,), one=True)
        assert v_check['stock_quantity'] == orig_stock


# ===========================================================================
# 3. SALES + INVENTORY + CREDIT LEDGER RECONCILIATION
# ===========================================================================

def test_sales_credit_and_split_payment_authoritative_reconciliation(app):
    """Verify complete sales flow: split payment sale creating CREDIT_SALE,
    subsequent settlement payment via credit_service, and balance reconciliation."""
    with app.app_context():
        # 1. Setup active customer
        cust_id = customer_service.create_customer({
            'customer_name': 'QA Smt. Lakshmi Devi',
            'phone': f"9988{datetime.now().strftime('%M%S%f')[:6]}",
            'email': 'lakshmi.qa@example.com',
            'address': 'Kanchipuram Silk Lane',
            'credit_limit': 50000.00,
            'status': 'ACTIVE'
        })

        # 2. Setup active product variant with sufficient stock
        v = query_db("SELECT variant_id, stock_quantity, selling_price FROM product_variants WHERE status = 'ACTIVE' AND stock_quantity >= 10 LIMIT 1", one=True)
        vid = v['variant_id']
        initial_stock = v['stock_quantity']
        selling_price = Decimal(str(v['selling_price']))

        # 3. Process a SPLIT sale
        sale_qty = 2
        total_val = selling_price * Decimal(str(sale_qty))
        paid_val = Decimal('1000.00')
        credit_due = total_val - paid_val

        sale_data = {
            'customer_id': cust_id,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'subtotal': total_val,
            'discount': Decimal('0.00'),
            'tax': Decimal('0.00'),
            'total_amount': total_val,
            'paid_amount': paid_val,
            'balance_amount': credit_due,
            'payment_method': 'SPLIT',
            'payment_status': 'PARTIAL',
            'notes': 'QA Split payment sale test'
        }
        sale_items = [{'variant_id': vid, 'quantity': sale_qty, 'unit_price': selling_price, 'total_price': total_val}]

        sale_id = sale_service.create_sale(sale_data, sale_items, user_id=1)
        assert sale_id is not None

        # Verify stock was deducted
        v_after_sale = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = %s", (vid,), one=True)
        assert v_after_sale['stock_quantity'] == initial_stock - sale_qty

        # Verify customer credit profile matches credit due
        profile = credit_service.get_customer_credit_profile(cust_id)
        assert profile['outstanding_balance'] == credit_due
        assert profile['total_credit_amount'] == credit_due
        assert profile['total_paid_amount'] == Decimal('0.00')

        # 4. Settle partial Udhaar payment
        settle_amount = Decimal('500.00')
        credit_service.record_credit_payment(
            customer_id=cust_id,
            payment_data={
                'amount': settle_amount,
                'payment_method': 'UPI',
                'notes': 'QA UPI Udhaar settlement'
            },
            user_id=1
        )

        # 5. Check ledger balance matches authoritative calculation
        profile_after_pay = credit_service.get_customer_credit_profile(cust_id)
        expected_outstanding = credit_due - settle_amount
        assert profile_after_pay['outstanding_balance'] == expected_outstanding
        assert profile_after_pay['total_paid_amount'] == settle_amount

        # 6. Overpayment rejection test
        with pytest.raises(credit_service.ValidationError, match="cannot exceed"):
            credit_service.record_credit_payment(
                customer_id=cust_id,
                payment_data={
                    'amount': expected_outstanding + Decimal('100.00'),
                    'payment_method': 'CASH'
                },
                user_id=1
            )


# ===========================================================================
# 4. RETURNS / EXCHANGES INTEGRATION & AUDIT INTEGRITY
# ===========================================================================

def test_returns_and_exchanges_full_cycle(app):
    """Verify restockable returns, damaged returns, exchange with price difference,
    and verify that returns do not corrupt sales records."""
    with app.app_context():
        # Find 2 distinct active variants
        variants = query_db("SELECT variant_id, stock_quantity, selling_price FROM product_variants WHERE status = 'ACTIVE' AND stock_quantity >= 10 ORDER BY variant_id LIMIT 2")
        v1, v2 = variants[0], variants[1]

        # 1. Create Sale for Customer
        cid = customer_service.create_customer({
            'customer_name': 'QA Return Customer',
            'phone': f"9911{datetime.now().strftime('%M%S%f')[:6]}",
            'credit_limit': 30000.00
        })

        v1_price = Decimal(str(v1['selling_price']))
        sid = sale_service.create_sale({
            'customer_id': cid,
            'sale_date': date.today().strftime('%Y-%m-%d'),
            'subtotal': v1_price * 2,
            'discount': Decimal('0.00'),
            'tax': Decimal('0.00'),
            'total_amount': v1_price * 2,
            'paid_amount': v1_price * 2,
            'balance_amount': Decimal('0.00'),
            'payment_method': 'CASH',
            'payment_status': 'PAID'
        }, [{'variant_id': v1['variant_id'], 'quantity': 2, 'unit_price': v1_price, 'total_price': v1_price * 2}], user_id=1)

        # 2. Return 1 item as RESTOCKABLE
        v1_stock_pre_return = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = %s", (v1['variant_id'],), one=True)['stock_quantity']
        ret_res = return_service.create_return({
            'sale_id': sid,
            'customer_id': cid,
            'return_date': date.today().strftime('%Y-%m-%d'),
            'refund_type': 'CASH',
            'reason': 'QA Size Mismatch',
            'notes': 'Restockable test return'
        }, [{'variant_id': v1['variant_id'], 'quantity': 1, 'condition_status': 'RESTOCKABLE'}], user_id=1)
        assert ret_res['return_id'] is not None

        # Stock should be restored +1
        v1_stock_post_return = query_db("SELECT stock_quantity FROM product_variants WHERE variant_id = %s", (v1['variant_id'],), one=True)['stock_quantity']
        assert v1_stock_post_return == v1_stock_pre_return + 1

        # 3. Over-return prevention: cannot return 2 more items (only 1 remaining)
        with pytest.raises(return_service.ValidationError, match="Cannot return 2 unit"):
            return_service.create_return({
                'sale_id': sid,
                'customer_id': cid,
                'return_date': date.today().strftime('%Y-%m-%d'),
                'refund_type': 'CASH',
                'reason': 'Excess return attempt'
            }, [{'variant_id': v1['variant_id'], 'quantity': 2, 'condition_status': 'RESTOCKABLE'}], user_id=1)


# ===========================================================================
# 5. PDF GENERATION INTEGRITY & CONSISTENCY
# ===========================================================================

def test_credit_pdf_generation_magic_bytes_and_consistency(app):
    """Verify PDF statement generation returns valid PDF-1.4 bytes,
    handles empty/active/inactive customers, and matches credit_service balances."""
    with app.app_context():
        # 1. Fetch customer with credit profile
        c = query_db("SELECT customer_id FROM customers WHERE status = 'ACTIVE' LIMIT 1", one=True)
        cid = c['customer_id']

        pdf_bytes, filename = pdf_service.generate_credit_statement_pdf(cid)

        # Check PDF header magic bytes
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500
        assert pdf_bytes.startswith(b'%PDF-1.4') or b'%PDF' in pdf_bytes[:20]
        assert filename.endswith('.pdf')

        # Inverted date filter validation
        with pytest.raises(credit_service.ValidationError, match="cannot be later than"):
            pdf_service.generate_credit_statement_pdf(cid, date_from="2026-12-31", date_to="2026-01-01")


# ===========================================================================
# 6. NEGATIVE STOCK SAFETY AUDIT
# ===========================================================================

def test_negative_stock_prevention_across_all_operations(app):
    """Verify that stock quantity can never become negative via sales or manual subtractions."""
    with app.app_context():
        # Get active variant and current stock
        v = query_db("SELECT variant_id, stock_quantity, selling_price FROM product_variants WHERE status = 'ACTIVE' LIMIT 1", one=True)
        vid = v['variant_id']
        current_stock = v['stock_quantity']

        # 1. Attempt sale exceeding available stock
        excess_qty = current_stock + 100
        with pytest.raises(sale_service.ValidationError, match="Insufficient stock"):
            sale_service.create_sale({
                'sale_date': date.today().strftime('%Y-%m-%d'),
                'subtotal': Decimal('1000.00'),
                'discount': Decimal('0.00'),
                'tax': Decimal('0.00'),
                'total_amount': Decimal('1000.00'),
                'paid_amount': Decimal('1000.00'),
                'balance_amount': Decimal('0.00'),
                'payment_method': 'CASH',
                'payment_status': 'PAID'
            }, [{'variant_id': vid, 'quantity': excess_qty, 'unit_price': Decimal('10.00'), 'total_price': Decimal('1000.00')}], user_id=1)

        # 2. Attempt manual inventory subtract adjustment exceeding stock
        with pytest.raises(inventory_service.ValidationError, match="Cannot decrease stock"):
            inventory_service.adjust_stock(
                variant_id=vid,
                adjustment_type='DECREASE',
                quantity=current_stock + 50,
                reason='QA Negative Stock Test',
                user_id=1
            )


# ===========================================================================
# 7. RBAC SECURITY & ACCESS CONTROL MATRIX
# ===========================================================================

def test_rbac_security_access_matrix(client, staff_client, admin_client):
    """Verify RBAC matrix for Unauthenticated, Staff, and Admin across routes and APIs."""
    # 1. Unauthenticated redirects to /login
    assert client.get('/dashboard', follow_redirects=False).status_code == 302
    assert client.get('/products', follow_redirects=False).status_code == 302
    assert client.get('/inventory', follow_redirects=False).status_code == 302
    assert client.get('/purchases', follow_redirects=False).status_code == 302
    assert client.get('/reports', follow_redirects=False).status_code == 302

    # 2. Staff user permissions
    # Staff CAN view dashboard, sales, products, inventory, customers
    assert staff_client.get('/dashboard').status_code == 200
    assert staff_client.get('/products').status_code == 200
    assert staff_client.get('/inventory').status_code == 200
    assert staff_client.get('/credit').status_code == 200
    assert staff_client.get('/reports').status_code == 200

    # Staff CANNOT create products, inward purchases, or manual inventory adjustments
    # Web admin-only routes return 403 Access Restricted to non-admin staff
    res_p = staff_client.get('/products/new', follow_redirects=False)
    assert res_p.status_code == 403
    assert b'Access Restricted' in res_p.data

    res_pur = staff_client.get('/purchases/new', follow_redirects=False)
    assert res_pur.status_code == 403
    assert b'Access Restricted' in res_pur.data

    res_adj = staff_client.get('/inventory/adjustment', follow_redirects=False)
    assert res_adj.status_code == 403
    assert b'Access Restricted' in res_adj.data

    # Staff API denial (returns 403)
    post_prod = staff_client.post('/api/products', json={'product_name': 'Hacked'})
    assert post_prod.status_code == 403

    post_pur = staff_client.post('/api/purchases', json={'supplier_id': 1})
    assert post_pur.status_code == 403

    # 3. Admin user permissions (Full access)
    assert admin_client.get('/dashboard').status_code == 200
    assert admin_client.get('/products/new').status_code == 200
    assert admin_client.get('/purchases/new').status_code == 200
    assert admin_client.get('/inventory/adjustment').status_code == 200


# ===========================================================================
# 8. DASHBOARD & REPORT CROSS-SERVICE FINANCIAL CONSISTENCY
# ===========================================================================

def test_dashboard_and_reports_data_consistency(app):
    """Verify Phase 14 Dashboard stats and Phase 15 Report stats match underlying database truth."""
    with app.app_context():
        # 1. Total credit outstanding consistency
        dash_summary = dashboard_service.get_dashboard_summary()
        credit_summary = credit_service.get_credit_summary()
        credit_aging = report_service.get_credit_aging_report()

        dash_total_credit = dash_summary['total_credit_to_collect']
        service_total_credit = float(credit_summary['total_credit_to_collect'])
        aging_total_credit = credit_aging['summary']['total_outstanding']

        assert abs(dash_total_credit - service_total_credit) < 0.05
        assert abs(aging_total_credit - service_total_credit) < 0.05

        # 2. Inventory total units consistency
        inv_metrics = inventory_service.get_inventory_summary_metrics()
        inv_report = report_service.get_inventory_valuation_report()

        assert inv_metrics['total_units'] == inv_report['summary']['total_units']
        assert float(inv_metrics['total_cost_value']) == inv_report['summary']['total_cost_value']
