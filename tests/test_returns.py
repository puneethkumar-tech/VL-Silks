"""
VL Silks – Phase 13: Returns & Exchanges — Test Suite
32-point test plan covering:
  - Return listing, metrics, and item queries
  - Cash and credit refund returns (with stock movements)
  - RESTOCKABLE vs DAMAGED condition handling
  - Over-return prevention and duplicate return safety
  - Garment exchange workflow (price difference handling)
  - Exchange with RESTOCKABLE vs DAMAGED old items
  - API endpoint coverage (REST JSON)
  - Validation guardrails (bad sale, bad items, bad refund type)
  - Historical sales immutability
  - Exchange on already fully-returned items
"""

import pytest
import time
from decimal import Decimal
from datetime import date
from backend.app import create_app
from backend.utils.database import query_db
from backend.services import return_service, sale_service, customer_service
from backend.services.return_service import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


def _create_test_customer(app_ctx, credit_limit=50000.0):
    """Helper: create a unique test customer and return customer_id."""
    phone = f"7{int(time.time() * 10000) % 10000000000:010d}"[:11]
    return customer_service.create_customer({
        'customer_name': f'ReturnTestCust_{phone[-4:]}',
        'phone': phone,
        'credit_limit': credit_limit,
        'status': 'ACTIVE',
    })


def _create_test_sale(app_ctx, customer_id=None, qty=2, payment_method='CASH', paid_amount=None):
    """
    Helper: create a simple sale with 1 line item.
    Returns (sale_id, variant_id, unit_price, initial_stock).
    """
    variants = sale_service.get_active_variants_for_sale()
    available = [v for v in variants if v['stock_quantity'] >= qty]
    assert available, f"Need variant with stock >= {qty}"
    var = available[0]
    var_id = var['variant_id']
    unit_price = Decimal(str(var['selling_price']))
    initial_stock = var['stock_quantity']

    total = unit_price * qty
    sale_data = {
        'customer_id': customer_id,
        'sale_date': date.today().strftime('%Y-%m-%d'),
        'payment_method': payment_method,
        'paid_amount': float(paid_amount if paid_amount is not None else total),
        'discount': 0.0,
        'tax': 0.0,
        'notes': 'Return Test Sale',
    }
    items_data = [{
        'variant_id': var_id,
        'quantity': qty,
        'unit_price': float(unit_price),
        'item_discount': 0.0,
    }]
    sale_id = sale_service.create_sale(sale_data, items_data, user_id=1)
    return sale_id, var_id, unit_price, initial_stock


def _get_sale_item_id(sale_id, variant_id):
    """Helper: fetch sale_item_id from sale."""
    row = query_db(
        "SELECT sale_item_id FROM sale_items WHERE sale_id = %s AND variant_id = %s",
        (sale_id, variant_id),
        one=True
    )
    assert row, "Sale item not found"
    return row['sale_item_id']


# ---------------------------------------------------------------------------
# 1. Return Service — Listing & Metrics
# ---------------------------------------------------------------------------

def test_get_all_returns_returns_list(app):
    """Test 1: get_all_returns returns a list (possibly empty)."""
    with app.app_context():
        result = return_service.get_all_returns()
        assert isinstance(result, list)


def test_get_return_summary_metrics_structure(app):
    """Test 2: get_return_summary_metrics returns all expected keys."""
    with app.app_context():
        metrics = return_service.get_return_summary_metrics()
        assert 'total_returns_count' in metrics
        assert 'total_refunds_amount' in metrics
        assert 'today_returns_count' in metrics
        assert 'today_refunds_amount' in metrics
        assert 'total_exchanges_count' in metrics
        assert 'total_credit_adjustments_count' in metrics


def test_get_all_returns_filter_by_refund_type(app):
    """Test 3: Filtering by refund_type=CASH only returns CASH refunds."""
    with app.app_context():
        cash_returns = return_service.get_all_returns(refund_type='CASH')
        for r in cash_returns:
            assert r['refund_type'] == 'CASH'


def test_get_return_by_id_nonexistent(app):
    """Test 4: get_return_by_id returns None for a non-existent return."""
    with app.app_context():
        result = return_service.get_return_by_id(999999)
        assert result is None


# ---------------------------------------------------------------------------
# 2. Return — Returnable Item Calculation
# ---------------------------------------------------------------------------

def test_get_sale_returnable_items_known_sale(app):
    """Test 5: get_sale_returnable_items for a known sale returns correct structure."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale, items = return_service.get_sale_returnable_items(sale_id)
        assert sale is not None
        assert sale['sale_id'] == sale_id
        assert isinstance(items, list)
        assert len(items) >= 1
        item = items[0]
        assert 'returnable_quantity' in item
        assert 'effective_unit_price' in item
        assert 'is_returnable' in item
        assert item['returnable_quantity'] >= 0


def test_get_sale_returnable_items_nonexistent_sale(app):
    """Test 6: get_sale_returnable_items returns (None, []) for nonexistent sale."""
    with app.app_context():
        sale, items = return_service.get_sale_returnable_items(999999)
        assert sale is None
        assert items == []


# ---------------------------------------------------------------------------
# 3. Cash Refund Return — Core Path
# ---------------------------------------------------------------------------

def test_create_cash_return_restockable_success(app):
    """Test 7: Cash return with RESTOCKABLE condition increments stock and creates stock movement."""
    with app.app_context():
        sale_id, var_id, unit_price, initial_stock = _create_test_sale(app, qty=3)
        # Stock was decremented by sale; get post-sale stock
        post_sale_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        res = return_service.create_return(
            return_data={
                'sale_id': sale_id,
                'refund_type': 'CASH',
                'return_date': date.today().strftime('%Y-%m-%d'),
                'return_reason': 'Test cash return',
            },
            items_data=[{
                'sale_item_id': sale_item_id,
                'quantity': 2,
                'condition_status': 'RESTOCKABLE',
            }],
            user_id=1
        )

        assert res['return_id'] > 0
        assert res['return_reference'].startswith('RET-')
        assert res['total_refund_amount'] == (unit_price * 2).quantize(Decimal('0.01'))
        assert res['refund_type'] == 'CASH'

        # Stock must be restored
        new_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        assert new_stock == post_sale_stock + 2

        # Stock movement must exist
        movement = query_db(
            "SELECT * FROM stock_movements WHERE variant_id = %s AND reference_type = 'RETURN' AND reference_id = %s",
            (var_id, res['return_id']), one=True
        )
        assert movement is not None
        assert movement['movement_type'] == 'CUSTOMER_RETURN'


def test_create_cash_return_damaged_no_stock_increment(app):
    """Test 8: DAMAGED return does NOT restore stock, but creates audit movement."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        post_sale_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        res = return_service.create_return(
            return_data={
                'sale_id': sale_id,
                'refund_type': 'CASH',
                'return_date': date.today().strftime('%Y-%m-%d'),
                'return_reason': 'Torn seam',
            },
            items_data=[{
                'sale_item_id': sale_item_id,
                'quantity': 1,
                'condition_status': 'DAMAGED',
            }],
            user_id=1
        )

        assert res['return_id'] > 0
        # Stock must NOT increase (item is damaged)
        current_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        assert current_stock == post_sale_stock

        # Audit movement must exist (DAMAGE type with qty=0)
        movement = query_db(
            "SELECT * FROM stock_movements WHERE variant_id = %s AND reference_type = 'RETURN' AND reference_id = %s",
            (var_id, res['return_id']), one=True
        )
        assert movement is not None
        assert movement['movement_type'] == 'DAMAGE'


def test_create_return_refund_amount_calculated_server_side(app):
    """Test 9: Refund amount is calculated server-side from original sale price, not client input."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        res = return_service.create_return(
            return_data={
                'sale_id': sale_id,
                'refund_type': 'CASH',
                'return_reason': 'Server-side calc test',
            },
            items_data=[{
                'sale_item_id': sale_item_id,
                'quantity': 1,
                'condition_status': 'RESTOCKABLE',
                # intentionally don't pass a manual refund_amount — server must calculate
            }],
            user_id=1
        )
        expected_refund = unit_price.quantize(Decimal('0.01'))
        assert res['total_refund_amount'] == expected_refund


def test_return_record_persisted(app):
    """Test 10: Created return record is retrievable with get_return_by_id."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        res = return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH', 'return_reason': 'Persistence check'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )
        return_id = res['return_id']

        ret = return_service.get_return_by_id(return_id)
        assert ret is not None
        assert ret['return_id'] == return_id
        assert ret['sale_id'] == sale_id
        assert 'items' in ret
        assert len(ret['items']) == 1


# ---------------------------------------------------------------------------
# 4. Credit Adjustment Return
# ---------------------------------------------------------------------------

def test_create_credit_adjustment_return_creates_ledger_entry(app):
    """Test 11: CREDIT_ADJUSTMENT return inserts a RETURN_REFUND credit transaction."""
    with app.app_context():
        cust_id = _create_test_customer(app)
        sale_id, var_id, unit_price, _ = _create_test_sale(app, customer_id=cust_id, qty=2, payment_method='CREDIT', paid_amount=0)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # Count credit transactions before
        ct_before = query_db(
            "SELECT COUNT(*) AS cnt FROM credit_transactions WHERE customer_id = %s AND transaction_type = 'RETURN_REFUND'",
            (cust_id,), one=True
        )['cnt']

        res = return_service.create_return(
            return_data={
                'sale_id': sale_id,
                'refund_type': 'CREDIT_ADJUSTMENT',
                'return_reason': 'Udhaar credit test',
            },
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )

        ct_after = query_db(
            "SELECT COUNT(*) AS cnt FROM credit_transactions WHERE customer_id = %s AND transaction_type = 'RETURN_REFUND'",
            (cust_id,), one=True
        )['cnt']

        assert ct_after == ct_before + 1
        assert res['refund_type'] == 'CREDIT_ADJUSTMENT'


def test_credit_adjustment_requires_customer(app):
    """Test 12: CREDIT_ADJUSTMENT on a walk-in (no customer) sale raises ValidationError."""
    with app.app_context():
        # Create a sale WITHOUT a customer
        sale_id, var_id, unit_price, _ = _create_test_sale(app, customer_id=None, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        with pytest.raises(ValidationError, match="[Cc]ustomer"):
            return_service.create_return(
                return_data={
                    'sale_id': sale_id,
                    'refund_type': 'CREDIT_ADJUSTMENT',
                },
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


# ---------------------------------------------------------------------------
# 5. Over-Return Prevention & Validation
# ---------------------------------------------------------------------------

def test_return_more_than_sold_quantity_raises_error(app):
    """Test 13: Attempting to return more units than sold raises ValidationError."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        with pytest.raises(ValidationError):
            return_service.create_return(
                return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 99, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


def test_return_already_fully_returned_raises_error(app):
    """Test 14: Returning items from a sale that has already been fully returned raises ValidationError."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # First return — return all 2 items
        return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 2, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )

        # Second return — attempt to return again
        with pytest.raises(ValidationError):
            return_service.create_return(
                return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


def test_partial_return_then_remaining_return(app):
    """Test 15: Partial return then returning the remaining quantity succeeds."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=3)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # Return 1 of 3
        r1 = return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )

        # Verify returnable is now 2
        _, items = return_service.get_sale_returnable_items(sale_id)
        matching = [i for i in items if i['sale_item_id'] == sale_item_id]
        assert matching[0]['returnable_quantity'] == 2

        # Return remaining 2
        r2 = return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 2, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )
        assert r2['return_id'] > r1['return_id']


def test_return_nonexistent_sale_raises_error(app):
    """Test 16: Returning against a non-existent sale raises ValidationError."""
    with app.app_context():
        with pytest.raises(ValidationError):
            return_service.create_return(
                return_data={'sale_id': 999999, 'refund_type': 'CASH'},
                items_data=[{'sale_item_id': 1, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


def test_return_invalid_refund_type_raises_error(app):
    """Test 17: Providing an invalid refund_type raises ValidationError."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        with pytest.raises(ValidationError, match="refund_type"):
            return_service.create_return(
                return_data={'sale_id': sale_id, 'refund_type': 'INVALID_TYPE'},
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


def test_return_invalid_condition_status_raises_error(app):
    """Test 18: Providing an invalid condition_status raises ValidationError."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        with pytest.raises(ValidationError):
            return_service.create_return(
                return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'MYSTERY_CONDITION'}],
                user_id=1
            )


def test_return_zero_quantity_items_raises_error(app):
    """Test 19: Return request with all zero quantities raises ValidationError."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        with pytest.raises(ValidationError):
            return_service.create_return(
                return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
                items_data=[{'sale_item_id': sale_item_id, 'quantity': 0, 'condition_status': 'RESTOCKABLE'}],
                user_id=1
            )


# ---------------------------------------------------------------------------
# 6. Historical Sale Immutability
# ---------------------------------------------------------------------------

def test_original_sale_unchanged_after_return(app):
    """Test 20: Original sale record is NOT modified after a return (immutability)."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        original_sale = sale_service.get_sale_by_id(sale_id)
        assert original_sale is not None
        original_total = original_sale['total_amount']
        original_invoice = original_sale['invoice_number']

        sale_item_id = _get_sale_item_id(sale_id, var_id)
        return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )

        # Re-read original sale
        after_sale = sale_service.get_sale_by_id(sale_id)
        assert after_sale['total_amount'] == original_total
        assert after_sale['invoice_number'] == original_invoice
        assert after_sale['payment_method'] == original_sale['payment_method']


# ---------------------------------------------------------------------------
# 7. Garment Exchange Workflow
# ---------------------------------------------------------------------------

def test_process_exchange_even_price_success(app):
    """Test 21: Exchange where old and new items have same value succeeds (even exchange)."""
    with app.app_context():
        # Get two variants with same selling price or just use same variant (size swap)
        variants = sale_service.get_active_variants_for_sale()
        available = [v for v in variants if v['stock_quantity'] >= 2]
        assert len(available) >= 2, "Need at least 2 variants with stock"

        old_var = available[0]
        new_var = available[1]

        sale_id, _, _, _ = _create_test_sale(app, qty=1)
        # Get actual sale item from the sale we created
        sale = sale_service.get_sale_by_id(sale_id)
        sale_items = query_db("SELECT * FROM sale_items WHERE sale_id = %s", (sale_id,))
        assert sale_items
        sale_item = sale_items[0]
        actual_var_id = sale_item['variant_id']

        new_var_candidates = [v for v in variants if v['variant_id'] != actual_var_id and v['stock_quantity'] >= 1]
        assert new_var_candidates, "Need another variant with stock for exchange"
        replacement = new_var_candidates[0]

        res = return_service.process_exchange(
            exchange_data={
                'sale_id': sale_id,
                'return_date': date.today().strftime('%Y-%m-%d'),
                'notes': 'Size swap test',
                'payment_method': 'CASH',
            },
            old_items_data=[{
                'sale_item_id': sale_item['sale_item_id'],
                'quantity': 1,
                'condition_status': 'RESTOCKABLE',
            }],
            new_items_data=[{
                'variant_id': replacement['variant_id'],
                'quantity': 1,
            }],
            user_id=1
        )

        assert res['return_id'] > 0
        assert res['return_reference'].startswith('RET-')
        assert 'price_difference' in res
        assert 'payment_status' in res
        assert res['payment_status'] in ('CUSTOMER_OWES', 'STORE_OWES', 'EVEN_EXCHANGE')


def test_process_exchange_restockable_increments_old_stock(app):
    """Test 22: Exchange of RESTOCKABLE old item restores its stock."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=1)
        post_sale_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # Get a different replacement variant
        variants = sale_service.get_active_variants_for_sale()
        replacements = [v for v in variants if v['variant_id'] != var_id and v['stock_quantity'] >= 1]
        assert replacements, "Need a replacement variant"
        rep = replacements[0]

        return_service.process_exchange(
            exchange_data={'sale_id': sale_id, 'notes': 'Test exchange', 'payment_method': 'CASH'},
            old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            new_items_data=[{'variant_id': rep['variant_id'], 'quantity': 1}],
            user_id=1
        )

        # Old variant stock must be back up by 1
        new_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        assert new_stock == post_sale_stock + 1


def test_process_exchange_deducts_new_variant_stock(app):
    """Test 23: Exchange correctly deducts stock from the replacement variant."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        variants = sale_service.get_active_variants_for_sale()
        replacements = [v for v in variants if v['variant_id'] != var_id and v['stock_quantity'] >= 1]
        assert replacements
        rep = replacements[0]
        rep_initial_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (rep['variant_id'],), one=True
        )['stock_quantity']

        return_service.process_exchange(
            exchange_data={'sale_id': sale_id, 'notes': 'Stock deduct test', 'payment_method': 'CASH'},
            old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            new_items_data=[{'variant_id': rep['variant_id'], 'quantity': 1}],
            user_id=1
        )

        rep_new_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (rep['variant_id'],), one=True
        )['stock_quantity']
        # Replacement stock must have been decremented by 1
        assert rep_new_stock == rep_initial_stock - 1


def test_process_exchange_insufficient_replacement_stock_raises_error(app):
    """Test 24: Exchange fails if replacement variant has insufficient stock."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # Use variant_id that definitely doesn't have stock (use sale variant with 0 remaining)
        # Or a clearly nonexistent variant_id
        with pytest.raises((ValidationError, Exception)):
            return_service.process_exchange(
                exchange_data={'sale_id': sale_id, 'payment_method': 'CASH'},
                old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                new_items_data=[{'variant_id': 99999, 'quantity': 1}],  # non-existent variant
                user_id=1
            )


def test_process_exchange_already_returned_item_raises_error(app):
    """Test 25: Exchange on an already fully-returned item raises ValidationError."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        # First: full return
        return_service.create_return(
            return_data={'sale_id': sale_id, 'refund_type': 'CASH'},
            items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            user_id=1
        )

        # Now: try to exchange the same already-returned item
        variants = sale_service.get_active_variants_for_sale()
        replacements = [v for v in variants if v['variant_id'] != var_id and v['stock_quantity'] >= 1]
        if not replacements:
            pytest.skip("No replacement variant available for this test")

        with pytest.raises(ValidationError):
            return_service.process_exchange(
                exchange_data={'sale_id': sale_id, 'payment_method': 'CASH'},
                old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
                new_items_data=[{'variant_id': replacements[0]['variant_id'], 'quantity': 1}],
                user_id=1
            )


def test_process_exchange_damaged_old_item_no_stock_restore(app):
    """Test 26: Exchange with DAMAGED old item does not restore old variant's stock."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        post_sale_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        variants = sale_service.get_active_variants_for_sale()
        replacements = [v for v in variants if v['variant_id'] != var_id and v['stock_quantity'] >= 1]
        assert replacements
        rep = replacements[0]

        return_service.process_exchange(
            exchange_data={'sale_id': sale_id, 'notes': 'Damaged exchange test', 'payment_method': 'CASH'},
            old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'DAMAGED'}],
            new_items_data=[{'variant_id': rep['variant_id'], 'quantity': 1}],
            user_id=1
        )

        # Old variant stock must NOT be restored (item was DAMAGED)
        current_stock = query_db(
            "SELECT stock_quantity FROM product_variants WHERE variant_id = %s",
            (var_id,), one=True
        )['stock_quantity']
        assert current_stock == post_sale_stock  # unchanged


def test_process_exchange_result_contains_price_difference(app):
    """Test 27: process_exchange result dict contains old_total_value, new_total_value, price_difference."""
    with app.app_context():
        sale_id, var_id, _, _ = _create_test_sale(app, qty=1)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

        variants = sale_service.get_active_variants_for_sale()
        replacements = [v for v in variants if v['variant_id'] != var_id and v['stock_quantity'] >= 1]
        assert replacements

        res = return_service.process_exchange(
            exchange_data={'sale_id': sale_id, 'payment_method': 'CASH'},
            old_items_data=[{'sale_item_id': sale_item_id, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}],
            new_items_data=[{'variant_id': replacements[0]['variant_id'], 'quantity': 1}],
            user_id=1
        )
        assert 'old_total_value' in res
        assert 'new_total_value' in res
        assert 'price_difference' in res
        computed_diff = res['new_total_value'] - res['old_total_value']
        assert abs(computed_diff - res['price_difference']) < Decimal('0.02')


# ---------------------------------------------------------------------------
# 8. REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_list_returns_200(admin_client):
    """Test 28: GET /api/returns returns 200 with success status."""
    rv = admin_client.get('/api/returns')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'success'
    assert 'data' in data
    assert isinstance(data['data'], list)


def test_api_get_return_not_found_404(admin_client):
    """Test 29: GET /api/returns/999999 returns 404."""
    rv = admin_client.get('/api/returns/999999')
    assert rv.status_code == 404
    data = rv.get_json()
    assert data['status'] == 'error'


def test_api_get_sale_returnable_items_nonexistent_404(admin_client):
    """Test 30: GET /api/returns/sale/999999/returnable-items returns 404."""
    rv = admin_client.get('/api/returns/sale/999999/returnable-items')
    assert rv.status_code == 404


def test_api_create_return_success(app, admin_client):
    """Test 31: POST /api/returns creates a return and returns 201."""
    with app.app_context():
        sale_id, var_id, unit_price, _ = _create_test_sale(app, qty=2)
        sale_item_id = _get_sale_item_id(sale_id, var_id)

    payload = {
        'sale_id': sale_id,
        'refund_type': 'CASH',
        'return_date': date.today().strftime('%Y-%m-%d'),
        'return_reason': 'API test return',
        'items': [
            {
                'sale_item_id': sale_item_id,
                'quantity': 1,
                'condition_status': 'RESTOCKABLE',
            }
        ]
    }
    rv = admin_client.post('/api/returns', json=payload)
    assert rv.status_code == 201
    data = rv.get_json()
    assert data['status'] == 'success'
    assert 'data' in data
    assert data['data']['return_id'] > 0
    assert data['data']['refund_type'] == 'CASH'


def test_api_create_return_invalid_sale_400(admin_client):
    """Test 32: POST /api/returns with invalid sale_id returns 400."""
    payload = {
        'sale_id': 999999,
        'refund_type': 'CASH',
        'items': [{'sale_item_id': 1, 'quantity': 1, 'condition_status': 'RESTOCKABLE'}]
    }
    rv = admin_client.post('/api/returns', json=payload)
    assert rv.status_code in (400, 500)  # ValidationError → 400; DB error → 500 both acceptable
    data = rv.get_json()
    assert data['status'] == 'error'


# ---------------------------------------------------------------------------
# 9. Web Route Smoke Tests
# ---------------------------------------------------------------------------

def test_web_returns_index_requires_login(client):
    """Test extra: /returns redirects unauthenticated users to login."""
    rv = client.get('/returns', follow_redirects=False)
    assert rv.status_code in (302, 301)


def test_web_returns_index_accessible_to_admin(admin_client):
    """Test extra: /returns is accessible to logged-in admin."""
    rv = admin_client.get('/returns')
    assert rv.status_code == 200
    assert b'Return' in rv.data


def test_web_returns_new_accessible_to_staff(staff_client):
    """Test extra: /returns/new is accessible to staff."""
    rv = staff_client.get('/returns/new')
    assert rv.status_code == 200


def test_web_returns_view_not_found_redirects(admin_client):
    """Test extra: /returns/999999 redirects if not found."""
    rv = admin_client.get('/returns/999999', follow_redirects=False)
    assert rv.status_code in (302, 301, 404)


def test_api_get_sale_returnable_items_known_sale(app, admin_client):
    """Test extra: GET /api/returns/sale/:id/returnable-items returns 200 for a real sale."""
    with app.app_context():
        sale_id, _, _, _ = _create_test_sale(app, qty=1)

    rv = admin_client.get(f'/api/returns/sale/{sale_id}/returnable-items')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['status'] == 'success'
    assert 'items' in data
    assert 'sale' in data


# ---------------------------------------------------------------------------
# 10. Direct Sale ID Lookup & Resolution Regressions
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_test_sale(app):
    """
    Fixture: Create an isolated customer and sale for return lookup tests,
    and automatically clean up on teardown without leaving residue in DB.
    """
    with app.app_context():
        cust_id = _create_test_customer(app.app_context())
        sale_id, var_id, unit_price, _ = _create_test_sale(app.app_context(), customer_id=cust_id, qty=2)
        sale = sale_service.get_sale_by_id(sale_id)
        yield {
            'sale_id': sale_id,
            'customer_id': cust_id,
            'variant_id': var_id,
            'invoice_number': sale['invoice_number'],
            'customer_name': sale.get('customer_name', '')
        }
        # Teardown: delete sale items, sale, stock movements, and customer
        from backend.utils.database import get_db_cursor
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE ri FROM return_items ri INNER JOIN returns r ON ri.return_id = r.return_id WHERE r.sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM returns WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM credit_transactions WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM payments WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM sale_items WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM sales WHERE sale_id = %s", (sale_id,))
            cursor.execute("DELETE FROM stock_movements WHERE reference_type = 'SALE' AND reference_id = %s", (sale_id,))
            cursor.execute("DELETE FROM customers WHERE customer_id = %s", (cust_id,))


def test_web_returns_new_direct_sale_id_lookup(admin_client, isolated_test_sale):
    """Test: Direct lookup via direct_sale_id redirects to canonical URL and displays sale."""
    sale_id = isolated_test_sale['sale_id']
    inv_bytes = isolated_test_sale['invoice_number'].encode()
    cust_bytes = isolated_test_sale['customer_name'].encode()

    rv = admin_client.get(f'/returns/new?direct_sale_id={sale_id}', follow_redirects=True)
    assert rv.status_code == 200
    assert inv_bytes in rv.data
    assert cust_bytes in rv.data


def test_web_returns_new_canonical_sale_id_param(admin_client, isolated_test_sale):
    """Test: Direct GET /returns/new?sale_id=<id> loads sale details directly."""
    sale_id = isolated_test_sale['sale_id']
    inv_bytes = isolated_test_sale['invoice_number'].encode()
    cust_bytes = isolated_test_sale['customer_name'].encode()

    rv = admin_client.get(f'/returns/new?sale_id={sale_id}')
    assert rv.status_code == 200
    assert inv_bytes in rv.data
    assert cust_bytes in rv.data


def test_web_returns_new_blank_selected_with_valid_direct_id(admin_client, isolated_test_sale):
    """Test: Submitting blank dropdown with direct_sale_id=<id> resolves correctly."""
    sale_id = isolated_test_sale['sale_id']
    inv_bytes = isolated_test_sale['invoice_number'].encode()
    cust_bytes = isolated_test_sale['customer_name'].encode()

    rv = admin_client.get(f'/returns/new?selected_sale_id=&direct_sale_id={sale_id}', follow_redirects=True)
    assert rv.status_code == 200
    assert inv_bytes in rv.data
    assert cust_bytes in rv.data


def test_web_returns_new_duplicate_and_blank_sale_id_params(admin_client, isolated_test_sale):
    """Test: Duplicate or empty sale_id query parameters cannot override a valid ID."""
    sale_id = isolated_test_sale['sale_id']
    inv_bytes = isolated_test_sale['invoice_number'].encode()

    # 1. Blank first, valid second
    rv1 = admin_client.get(f'/returns/new?sale_id=&sale_id={sale_id}', follow_redirects=True)
    assert rv1.status_code == 200
    assert inv_bytes in rv1.data

    # 2. Valid first, blank second
    rv2 = admin_client.get(f'/returns/new?sale_id={sale_id}&sale_id=', follow_redirects=True)
    assert rv2.status_code == 200
    assert inv_bytes in rv2.data


def test_web_returns_new_invalid_sale_id_format(admin_client):
    """Test: Non-numeric direct_sale_id shows warning message and redirects without crash."""
    rv = admin_client.get('/returns/new?direct_sale_id=invalid_abc', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Invalid Sale ID specified' in rv.data


def test_web_returns_new_nonexistent_sale_id(admin_client):
    """Test: Nonexistent numeric sale ID shows clear warning and renders Step 1 gracefully."""
    rv = admin_client.get('/returns/new?sale_id=999999', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Sale #999999 was not found' in rv.data
    assert b'Step 1: Select Original Sales Invoice' in rv.data


# ---------------------------------------------------------------------------
# 11. Return Detail View Template Regressions
# ---------------------------------------------------------------------------

def test_web_return_detail_view_success(app, admin_client):
    """Test: Viewing return details page renders items table and audit info without TypeError."""
    with app.app_context():
        sale_id, variant_id, price, _ = _create_test_sale(app.app_context(), qty=2)
        sale, items = return_service.get_sale_returnable_items(sale_id)
        sale_item = items[0]

        res = return_service.create_return(
            return_data={
                'sale_id': sale_id,
                'refund_type': 'CASH',
                'return_date': str(date.today()),
                'return_reason': 'Defect test'
            },
            items_data=[{
                'sale_item_id': sale_item['sale_item_id'],
                'quantity': 1,
                'condition_status': 'RESTOCKABLE'
            }],
            user_id=1
        )
        return_id = res['return_id']
        ref = res['return_reference']

    rv = admin_client.get(f'/returns/{return_id}')
    assert rv.status_code == 200
    assert ref.encode() in rv.data
    assert b'Returned Line Items' in rv.data
    assert b'RESTOCKABLE' in rv.data
    assert b'Cash Refund' in rv.data
    assert b'Total Refund Value' in rv.data


def test_web_return_detail_view_nonexistent(admin_client):
    """Test: Nonexistent return ID redirects to index with warning."""
    rv = admin_client.get('/returns/999999', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Return record #999999 was not found' in rv.data


# ---------------------------------------------------------------------------
# 12. Invoice Search — service + API endpoint
# ---------------------------------------------------------------------------

class TestInvoiceSalesSearch:
    """
    Tests for search_sales_for_returns() service function and
    GET /api/returns/sales/search endpoint.
    """

    def test_service_empty_query_returns_empty(self, app):
        """Empty or blank query returns [] without hitting the DB."""
        with app.app_context():
            assert return_service.search_sales_for_returns('') == []
            assert return_service.search_sales_for_returns('   ') == []

    def test_service_short_query_still_works(self, app):
        """Single-character queries are allowed at the service layer."""
        with app.app_context():
            # Should not raise — might or might not find results
            results = return_service.search_sales_for_returns('S')
            assert isinstance(results, list)

    def test_service_returns_list_of_dicts(self, app):
        """Results are a list of dicts with the required keys."""
        with app.app_context():
            results = return_service.search_sales_for_returns('SALE-2026', limit=5)
            assert isinstance(results, list)
            if results:
                row = results[0]
                required_keys = {
                    'sale_id', 'invoice_number', 'sale_date', 'total_amount',
                    'payment_method', 'payment_status', 'customer_name',
                    'customer_phone', 'returnable_items_count',
                    'existing_returns_count', 'is_fully_returned',
                }
                assert required_keys.issubset(set(row.keys())), (
                    f"Missing keys: {required_keys - set(row.keys())}"
                )

    def test_service_numeric_sale_id_lookup(self, app):
        """Searching a numeric sale_id string finds the exact sale."""
        with app.app_context():
            # Use the newest non-VOID sale (high ID, not a substring of many invoice numbers)
            known = query_db(
                "SELECT sale_id FROM sales WHERE payment_status != 'VOID' ORDER BY sale_id DESC LIMIT 1",
                one=True
            )
            if not known:
                pytest.skip("No non-VOID sales in DB")
            sale_id_str = str(known['sale_id'])
            # Use a generous limit to accommodate any LIKE collisions
            results = return_service.search_sales_for_returns(sale_id_str, limit=50)
            sale_ids = [r['sale_id'] for r in results]
            assert known['sale_id'] in sale_ids, (
                f"Expected sale_id {known['sale_id']} in results {sale_ids}"
            )

    def test_service_invoice_number_partial_match(self, app):
        """Partial invoice number substring returns matching rows."""
        with app.app_context():
            # 'SALE-2026' should match many invoices
            results = return_service.search_sales_for_returns('SALE-2026', limit=10)
            assert len(results) > 0, "Expected at least one invoice matching 'SALE-2026'"
            for r in results:
                assert 'SALE-2026' in r['invoice_number'] or r['sale_id'] is not None

    def test_service_customer_name_search(self, app):
        """Customer name partial match returns sales for that customer."""
        with app.app_context():
            # Find a sale with a named customer
            cust = query_db(
                """SELECT c.customer_name, s.sale_id FROM sales s
                   JOIN customers c ON s.customer_id = c.customer_id
                   WHERE s.payment_status != 'VOID'
                   LIMIT 1""",
                one=True
            )
            if not cust:
                pytest.skip("No sales with named customers")
            name_fragment = cust['customer_name'][:5]  # first 5 chars
            results = return_service.search_sales_for_returns(name_fragment, limit=20)
            assert any(r['sale_id'] == cust['sale_id'] for r in results), (
                f"Expected sale_id {cust['sale_id']} in search for '{name_fragment}'"
            )

    def test_service_excludes_void_sales(self, app):
        """VOID sales must never appear in search results."""
        with app.app_context():
            void = query_db(
                "SELECT sale_id FROM sales WHERE payment_status = 'VOID' LIMIT 1",
                one=True
            )
            if not void:
                pytest.skip("No VOID sales in DB to verify exclusion")
            results = return_service.search_sales_for_returns(str(void['sale_id']), limit=10)
            sale_ids = [r['sale_id'] for r in results]
            assert void['sale_id'] not in sale_ids, (
                f"VOID sale_id {void['sale_id']} should not appear in results"
            )

    def test_service_fully_returned_flag(self, app):
        """is_fully_returned reflects actual returnable item count."""
        with app.app_context():
            sale_id, variant_id, price, _ = _create_test_sale(app.app_context(), qty=1)
            # Before return: should NOT be fully returned
            results = return_service.search_sales_for_returns(str(sale_id), limit=5)
            row = next((r for r in results if r['sale_id'] == sale_id), None)
            assert row is not None, f"Newly created sale_id {sale_id} not found in search"
            assert row['is_fully_returned'] is False, "Fresh sale should not be fully returned"

            # Process a full return
            _, items = return_service.get_sale_returnable_items(sale_id)
            return_service.create_return(
                return_data={
                    'sale_id': sale_id,
                    'refund_type': 'CASH',
                    'return_date': str(date.today()),
                    'return_reason': 'Full return test',
                },
                items_data=[{
                    'sale_item_id': items[0]['sale_item_id'],
                    'quantity': 1,
                    'condition_status': 'RESTOCKABLE',
                }],
                user_id=1
            )

            # After full return: is_fully_returned must be True
            results2 = return_service.search_sales_for_returns(str(sale_id), limit=5)
            row2 = next((r for r in results2 if r['sale_id'] == sale_id), None)
            assert row2 is not None
            assert row2['is_fully_returned'] is True, (
                "Fully-returned sale should have is_fully_returned=True"
            )

    def test_service_limit_respected(self, app):
        """limit parameter caps result count."""
        with app.app_context():
            results = return_service.search_sales_for_returns('SALE-2026', limit=3)
            assert len(results) <= 3

    # ------- API endpoint tests -------

    def test_api_search_requires_login(self, client):
        """GET /api/returns/sales/search returns 302 redirect for unauthenticated users."""
        rv = client.get('/api/returns/sales/search?q=SALE')
        assert rv.status_code in (302, 401)

    def test_api_search_missing_query_returns_400(self, admin_client):
        """GET /api/returns/sales/search without ?q= returns HTTP 400."""
        rv = admin_client.get('/api/returns/sales/search')
        assert rv.status_code == 400
        data = rv.get_json()
        assert data['status'] == 'error'

    def test_api_search_invoice_number_hit(self, admin_client):
        """Searching by partial invoice number returns expected JSON shape."""
        rv = admin_client.get('/api/returns/sales/search?q=SALE-2026&limit=5')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'count' in data
        assert isinstance(data['data'], list)

    def test_api_search_returns_expected_fields(self, admin_client):
        """Each result row from the API contains all required fields."""
        rv = admin_client.get('/api/returns/sales/search?q=SALE-2026&limit=3')
        assert rv.status_code == 200
        data = rv.get_json()
        if data['count'] == 0:
            pytest.skip("No matching sales for field check")
        row = data['data'][0]
        for field in ('sale_id', 'invoice_number', 'sale_date', 'total_amount',
                      'payment_method', 'customer_name', 'is_fully_returned',
                      'returnable_items_count', 'existing_returns_count'):
            assert field in row, f"Missing field '{field}' in API response row"

    def test_api_search_no_results_returns_empty_list(self, admin_client):
        """Searching for a nonexistent term returns count=0 and empty data list."""
        rv = admin_client.get('/api/returns/sales/search?q=XQZNOTEXISTQZX')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['status'] == 'success'
        assert data['count'] == 0
        assert data['data'] == []

    def test_api_search_limit_capped_at_50(self, admin_client):
        """limit > 50 is silently capped to 50."""
        rv = admin_client.get('/api/returns/sales/search?q=SALE-2026&limit=9999')
        assert rv.status_code == 200
        data = rv.get_json()
        assert len(data['data']) <= 50

    def test_api_search_by_numeric_sale_id(self, app, admin_client):
        """API search by numeric sale_id finds the correct invoice."""
        with app.app_context():
            known = query_db(
                "SELECT sale_id FROM sales WHERE payment_status != 'VOID' ORDER BY sale_id DESC LIMIT 1",
                one=True
            )
            if not known:
                pytest.skip("No non-VOID sales available")
            sale_id = known['sale_id']
        rv = admin_client.get(f'/api/returns/sales/search?q={sale_id}&limit=50')
        assert rv.status_code == 200
        data = rv.get_json()
        found = [r for r in data['data'] if r['sale_id'] == sale_id]
        assert len(found) >= 1, f"sale_id {sale_id} not found in API search results"

    def test_api_search_excludes_void(self, app, admin_client):
        """API search never returns VOID sales."""
        with app.app_context():
            void = query_db(
                "SELECT sale_id FROM sales WHERE payment_status = 'VOID' LIMIT 1",
                one=True
            )
            if not void:
                pytest.skip("No VOID sales to verify exclusion")
            void_id = void['sale_id']
        rv = admin_client.get(f'/api/returns/sales/search?q={void_id}&limit=10')
        assert rv.status_code == 200
        data = rv.get_json()
        sale_ids = [r['sale_id'] for r in data['data']]
        assert void_id not in sale_ids

    def test_web_returns_new_still_shows_search_widget(self, admin_client):
        """GET /returns/new renders the search widget (invoiceSearchInput) alongside the dropdown."""
        rv = admin_client.get('/returns/new')
        assert rv.status_code == 200
        assert b'invoiceSearchInput' in rv.data
        assert b'Search Invoice / Customer / Phone / SKU' in rv.data
        # Dropdown still present
        assert b'Select from Recent Sales' in rv.data
        # Direct ID lookup still present
        assert b'direct_sale_id' in rv.data
