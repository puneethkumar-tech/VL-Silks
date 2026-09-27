import pytest
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import supplier_service
from backend.services.supplier_service import ValidationError


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
# 1. Supplier List, Search & Purchase Counts
# ---------------------------------------------------------------------------
def test_get_all_suppliers(app):
    """Test fetching all suppliers with purchase count and value."""
    with app.app_context():
        suppliers = supplier_service.get_all_suppliers()
        assert len(suppliers) >= 4  # 4 seed suppliers

        names = [s['supplier_name'] for s in suppliers]
        assert 'Sri Kanchi Silk Handloom Weavers Society' in names
        assert 'Tirupur Knitwear & Garments Hub' in names

        # Kanchi weavers (id=1) has purchase history in seed
        kanchi = next(s for s in suppliers if s['supplier_id'] == 1)
        assert kanchi['purchase_count'] >= 1
        assert kanchi['total_purchase_value'] > 0


def test_supplier_search(app):
    """Test supplier search across name, contact person, phone, email."""
    with app.app_context():
        # Search by partial name
        res1 = supplier_service.get_all_suppliers(search='Kanchi')
        assert len(res1) >= 1

        # Search non-existent
        res2 = supplier_service.get_all_suppliers(search='SUPPLIER_NONEXISTENT_XYZ')
        assert len(res2) == 0

        # Status filter
        res3 = supplier_service.get_all_suppliers(status='ACTIVE')
        assert all(s['status'] == 'ACTIVE' for s in res3)


# ---------------------------------------------------------------------------
# 2. Supplier Creation & Validation
# ---------------------------------------------------------------------------
def test_create_supplier_success(app):
    """Test creating a valid supplier and verifying its retrieval."""
    with app.app_context():
        sup_id = supplier_service.create_supplier({
            'supplier_name': 'Test Bangalore Cotton Mills',
            'contact_person': 'Ravi Shankar',
            'phone': '9900123456',
            'email': 'test.bcm@example.com',
            'address': '100 Test Street, Bengaluru',
            'gst_number': '29TESTGST1234Z',
            'status': 'ACTIVE'
        })
        assert sup_id > 0

        supplier = supplier_service.get_supplier_by_id(sup_id)
        assert supplier is not None
        assert supplier['supplier_name'] == 'Test Bangalore Cotton Mills'
        assert supplier['phone'] == '9900123456'

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (sup_id,))


def test_create_supplier_missing_name(app):
    """Supplier without a name should raise ValidationError."""
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            supplier_service.create_supplier({
                'supplier_name': '',
                'phone': '9900000001'
            })
        assert 'required' in str(exc.value).lower()


def test_create_supplier_missing_phone(app):
    """Supplier without a phone should raise ValidationError."""
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            supplier_service.create_supplier({
                'supplier_name': 'Valid Supplier Name',
                'phone': ''
            })
        assert 'phone' in str(exc.value).lower()


def test_create_supplier_invalid_email(app):
    """Supplier with an invalid email format should raise ValidationError."""
    with app.app_context():
        with pytest.raises(ValidationError) as exc:
            supplier_service.create_supplier({
                'supplier_name': 'Valid Supplier Name',
                'phone': '9900000002',
                'email': 'not-an-email'
            })
        assert 'email' in str(exc.value).lower()


# ---------------------------------------------------------------------------
# 3. Supplier Update & Status Toggle
# ---------------------------------------------------------------------------
def test_update_supplier(app):
    """Test updating an existing supplier's details."""
    with app.app_context():
        sup_id = supplier_service.create_supplier({
            'supplier_name': 'Temp Update Supplier',
            'phone': '9911111111',
            'status': 'ACTIVE'
        })

        supplier_service.update_supplier(sup_id, {
            'supplier_name': 'Temp Update Supplier RENAMED',
            'phone': '9922222222',
            'contact_person': 'New Contact',
            'status': 'ACTIVE'
        })

        updated = supplier_service.get_supplier_by_id(sup_id)
        assert updated['supplier_name'] == 'Temp Update Supplier RENAMED'
        assert updated['phone'] == '9922222222'
        assert updated['contact_person'] == 'New Contact'

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (sup_id,))


def test_toggle_supplier_status(app):
    """Test safely toggling supplier status."""
    with app.app_context():
        sup_id = supplier_service.create_supplier({
            'supplier_name': 'Temp Toggle Supplier',
            'phone': '9933333333',
            'status': 'ACTIVE'
        })

        # Deactivate
        status1 = supplier_service.toggle_supplier_status(sup_id, 'INACTIVE')
        assert status1 == 'INACTIVE'
        sup = supplier_service.get_supplier_by_id(sup_id)
        assert sup['status'] == 'INACTIVE'

        # Re-activate
        status2 = supplier_service.toggle_supplier_status(sup_id, 'ACTIVE')
        assert status2 == 'ACTIVE'

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (sup_id,))


def test_deactivation_preserves_purchase_history(app):
    """Deactivating a supplier preserves existing purchase records."""
    with app.app_context():
        # Supplier 1 (Kanchi) has purchases
        supplier_service.toggle_supplier_status(1, 'INACTIVE')

        # Purchases from supplier 1 still exist
        purchases = supplier_service.get_supplier_purchase_history(1)
        assert len(purchases) >= 1

        # Restore
        supplier_service.toggle_supplier_status(1, 'ACTIVE')


# ---------------------------------------------------------------------------
# 4. Purchase History
# ---------------------------------------------------------------------------
def test_supplier_purchase_history(app):
    """Test fetching purchase history for a supplier."""
    with app.app_context():
        # Supplier 1 has purchases in seed data
        purchases = supplier_service.get_supplier_purchase_history(1)
        assert len(purchases) >= 1

        first = purchases[0]
        assert 'invoice_number' in first
        assert 'total' in first
        assert first['total'] > 0


# ---------------------------------------------------------------------------
# 5. Web Routes & Role Permissions
# ---------------------------------------------------------------------------
def test_supplier_list_unauthenticated_redirects(client):
    """Unauthenticated users must be redirected to login."""
    res = client.get('/suppliers')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']


def test_supplier_list_staff_can_view(staff_client):
    """Staff can view the suppliers list."""
    res = staff_client.get('/suppliers')
    assert res.status_code == 200
    assert b'Supplier Directory' in res.data


def test_supplier_new_staff_denied(staff_client):
    """Staff cannot access /suppliers/new."""
    res = staff_client.get('/suppliers/new', follow_redirects=True)
    assert b'Administrator access required' in res.data


def test_supplier_view_page(admin_client):
    """Admin can view supplier profile page for seed supplier 1."""
    res = admin_client.get('/suppliers/1')
    assert res.status_code == 200
    assert b'Sri Kanchi Silk Handloom Weavers Society' in res.data
    assert b'Purchase History' in res.data


def test_supplier_edit_page_admin(admin_client):
    """Admin can access edit page for seed supplier."""
    res = admin_client.get('/suppliers/1/edit')
    assert res.status_code == 200
    assert b'Edit Supplier Details' in res.data


def test_supplier_not_found(admin_client):
    """Requesting non-existent supplier should redirect with flash."""
    res = admin_client.get('/suppliers/99999', follow_redirects=True)
    assert b'Supplier not found' in res.data


# ---------------------------------------------------------------------------
# 6. REST API Endpoints
# ---------------------------------------------------------------------------
def test_api_suppliers_list(client):
    """GET /api/suppliers returns list of suppliers."""
    res = client.get('/api/suppliers')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['count'] >= 4


def test_api_supplier_get_single(client):
    """GET /api/suppliers/:id returns correct supplier."""
    res = client.get('/api/suppliers/1')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert 'Kanchi' in data['data']['supplier_name']


def test_api_supplier_get_purchases(client):
    """GET /api/suppliers/:id/purchases returns purchase history."""
    res = client.get('/api/suppliers/1/purchases')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['count'] >= 1


def test_api_supplier_not_found(client):
    """GET /api/suppliers/:id for non-existent supplier returns 404."""
    res = client.get('/api/suppliers/99999')
    assert res.status_code == 404


def test_api_admin_supplier_create_update_delete(app, admin_client):
    """Test POST, PUT, DELETE on /api/suppliers (Admin)."""
    # POST: Create
    res_post = admin_client.post('/api/suppliers', json={
        'supplier_name': 'API Test Supplier Co',
        'phone': '9977777777',
        'contact_person': 'Test Person',
        'email': 'apitest@supplier.com'
    })
    assert res_post.status_code == 201
    sup_id = res_post.get_json()['supplier_id']

    # PUT: Update
    res_put = admin_client.put(f'/api/suppliers/{sup_id}', json={
        'supplier_name': 'API Test Supplier Co UPDATED',
        'phone': '9988888888'
    })
    assert res_put.status_code == 200

    # DELETE (deactivation)
    res_del = admin_client.delete(f'/api/suppliers/{sup_id}')
    assert res_del.status_code == 200
    assert 'safely deactivated' in res_del.get_json()['message']

    # Verify INACTIVE status (must use app context to hit test DB)
    with app.app_context():
        sup = supplier_service.get_supplier_by_id(sup_id)
    assert sup is not None, f"Supplier {sup_id} not found after deactivation"
    assert sup['status'] == 'INACTIVE'

    # Clean up
    with app.app_context():
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM suppliers WHERE supplier_id = %s", (sup_id,))


def test_api_supplier_create_unauthorized(client):
    """Unauthenticated POST to /api/suppliers should be rejected."""
    res = client.post('/api/suppliers', json={
        'supplier_name': 'Unauthorized Supplier',
        'phone': '9900000000'
    })
    assert res.status_code == 403
