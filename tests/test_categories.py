import pytest
import uuid
from backend.app import create_app
from backend.utils.database import query_db, get_db_cursor
from backend.services import category_service, product_service
from backend.services.category_service import ValidationError

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
# 1. Category List, Search & Product Counts
# ---------------------------------------------------------------------------
def test_get_all_categories(app):
    """Test fetching all categories with accurate product counts."""
    with app.app_context():
        categories = category_service.get_all_categories(include_counts=True)
        assert len(categories) >= 7
        cat_names = [c['category_name'] for c in categories]
        assert 'Sarees' in cat_names
        assert 'Shirts & Formals' in cat_names

        # Sarees has products associated in seed data
        saree_cat = next(c for c in categories if c['category_name'] == 'Sarees')
        assert saree_cat['product_count'] >= 2

def test_category_search_and_filter(app):
    """Test category search by keyword and status filtering."""
    with app.app_context():
        # Search by name
        res1 = category_service.get_all_categories(search='Silk')
        assert len(res1) > 0

        # Search non-existent
        res2 = category_service.get_all_categories(search='NON_EXISTENT_CAT_XYZ')
        assert len(res2) == 0

        # Filter by ACTIVE
        res3 = category_service.get_all_categories(status='ACTIVE')
        assert all(c['status'] == 'ACTIVE' for c in res3)


# ---------------------------------------------------------------------------
# 2. Category Creation & Duplicate Name Rejection
# ---------------------------------------------------------------------------
def test_create_category_and_duplicate_rejection(app):
    """Test category creation and case-insensitive/whitespace trimmed duplicate validation."""
    with app.app_context():
        # 1. Create unique category
        cat_id = category_service.create_category({
            'category_name': 'Test Bridal Lehengas',
            'description': 'Heavy embroidered bridal wear',
            'status': 'ACTIVE'
        })
        assert cat_id > 0

        cat = category_service.get_category_by_id(cat_id)
        assert cat['category_name'] == 'Test Bridal Lehengas'

        # 2. Duplicate exact name rejection
        with pytest.raises(ValidationError) as exc1:
            category_service.create_category({
                'category_name': 'Test Bridal Lehengas'
            })
        assert 'already exists' in str(exc1.value)

        # 3. Duplicate with leading/trailing whitespace and different casing
        with pytest.raises(ValidationError) as exc2:
            category_service.create_category({
                'category_name': '  test bridal lehengas  '
            })
        assert 'already exists' in str(exc2.value)

        # 4. Empty name rejection
        with pytest.raises(ValidationError) as exc3:
            category_service.create_category({
                'category_name': '   '
            })
        assert 'required' in str(exc3.value).lower()

        # Clean up test category
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM categories WHERE category_id = %s", (cat_id,))


# ---------------------------------------------------------------------------
# 3. Category Edit & Status Toggling (Safe Deactivation)
# ---------------------------------------------------------------------------
def test_category_edit_and_status_toggle(app):
    """Test updating category details and safely toggling active/inactive status."""
    with app.app_context():
        # Create temp category for testing update/toggle
        cat_id = category_service.create_category({
            'category_name': 'Temp Testing Category',
            'description': 'Temporary description',
            'status': 'ACTIVE'
        })

        # Update category
        category_service.update_category(cat_id, {
            'category_name': 'Temp Testing Category Updated',
            'description': 'Updated description',
            'status': 'ACTIVE'
        })
        cat = category_service.get_category_by_id(cat_id)
        assert cat['category_name'] == 'Temp Testing Category Updated'
        assert cat['description'] == 'Updated description'

        # Deactivate
        status_after_deact = category_service.toggle_category_status(cat_id, 'INACTIVE')
        assert status_after_deact == 'INACTIVE'
        cat_deact = category_service.get_category_by_id(cat_id)
        assert cat_deact['status'] == 'INACTIVE'

        # Reactivate
        status_after_react = category_service.toggle_category_status(cat_id, 'ACTIVE')
        assert status_after_react == 'ACTIVE'

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM categories WHERE category_id = %s", (cat_id,))


# ---------------------------------------------------------------------------
# 4. Product Integration & Exclusion of Inactive Categories
# ---------------------------------------------------------------------------
def test_inactive_category_excluded_from_new_product_dropdown(app):
    """Inactive categories must be excluded from product dropdown by default, but existing products remain accessible."""
    with app.app_context():
        # Create an inactive category
        cat_id = category_service.create_category({
            'category_name': 'Test Inactive Season Wear',
            'status': 'INACTIVE'
        })

        # Product service get_all_categories(status='ACTIVE') should NOT contain it
        active_cats = product_service.get_all_categories(status='ACTIVE')
        active_cat_ids = [c['category_id'] for c in active_cats]
        assert cat_id not in active_cat_ids

        # Category service get_all_categories() includes it when status is ALL or None
        all_cats = category_service.get_all_categories()
        all_cat_ids = [c['category_id'] for c in all_cats]
        assert cat_id in all_cat_ids

        # Clean up
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM categories WHERE category_id = %s", (cat_id,))

def test_existing_products_accessible_if_category_deactivated(app):
    """Deactivating a category does not delete or break existing product records."""
    with app.app_context():
        # Deactivate category 7 (Kids Festive Wear)
        category_service.toggle_category_status(7, 'INACTIVE')

        # Product 9 (Traditional Kids Pattu Pavadai Set) is in category 7
        p = product_service.get_product_by_id(9)
        assert p is not None
        assert p['product_name'] == 'Traditional Kids Pattu Pavadai Set'
        assert p['category_name'] == 'Kids Festive Wear'

        # Product variants for product 9 still exist
        variants = product_service.get_product_variants(9)
        assert len(variants) > 0

        # Restore category 7 to ACTIVE
        category_service.toggle_category_status(7, 'ACTIVE')


# ---------------------------------------------------------------------------
# 5. Web Routes & Role Permissions
# ---------------------------------------------------------------------------
def test_category_web_routes_unauthenticated(client):
    """Unauthenticated users must be redirected to login."""
    res = client.get('/categories')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']

def test_category_web_routes_staff_permissions(staff_client):
    """Staff can view categories list, but cannot access /categories/new or edit."""
    # Staff views categories list
    res_list = staff_client.get('/categories')
    assert res_list.status_code == 200
    assert b'Category Directory' in res_list.data

    # Staff tries to access /categories/new
    res_new = staff_client.get('/categories/new', follow_redirects=True)
    assert b'Administrator access required' in res_new.data

    # Staff tries to edit category
    res_edit = staff_client.get('/categories/1/edit', follow_redirects=True)
    assert b'Administrator access required' in res_edit.data

def test_category_web_routes_admin_crud(admin_client):
    """Admin has full access to add, edit, and view categories."""
    res_list = admin_client.get('/categories')
    assert res_list.status_code == 200

    res_new = admin_client.get('/categories/new')
    assert res_new.status_code == 200
    assert b'Create Garment Category' in res_new.data

    res_edit = admin_client.get('/categories/1/edit')
    assert res_edit.status_code == 200
    assert b'Edit Garment Category' in res_edit.data


# ---------------------------------------------------------------------------
# 6. REST API Endpoints (API_SPEC.md)
# ---------------------------------------------------------------------------
def test_api_categories_list_and_get(client):
    """Test GET /api/categories and GET /api/categories/:id."""
    res = client.get('/api/categories')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'success'
    assert data['count'] >= 7

    res_single = client.get('/api/categories/1')
    assert res_single.status_code == 200
    single_data = res_single.get_json()
    assert single_data['status'] == 'success'
    assert single_data['data']['category_name'] == 'Sarees'

def test_api_admin_category_crud_and_safe_delete(app, admin_client):
    """Test POST, PUT, and safe DELETE on /api/categories."""
    uid = uuid.uuid4().hex[:8]
    cat_id = None
    try:
        # 1. Create via API (unique name to avoid collisions across runs)
        res_post = admin_client.post('/api/categories', json={
            'category_name': f'API Test Cat {uid}',
            'description': 'Created via REST API'
        })
        assert res_post.status_code == 201
        cat_id = res_post.get_json()['category_id']

        # 2. Update via API (unique updated name)
        res_put = admin_client.put(f'/api/categories/{cat_id}', json={
            'category_name': f'API Test Cat {uid} Updated',
            'description': 'Updated description via REST API'
        })
        assert res_put.status_code == 200

        # 3. Safe Delete (Deactivation) via API
        res_del = admin_client.delete(f'/api/categories/{cat_id}')
        assert res_del.status_code == 200
        assert 'safely deactivated' in res_del.get_json()['message']

        # Verify status is now INACTIVE in database (use app context to hit test DB)
        with app.app_context():
            cat = category_service.get_category_by_id(cat_id)
        assert cat is not None, f"Category {cat_id} not found after deactivation"
        assert cat['status'] == 'INACTIVE'

    finally:
        # Always clean up — even if an assertion failed mid-test
        if cat_id is not None:
            with app.app_context():
                with get_db_cursor(commit=True) as cursor:
                    cursor.execute("DELETE FROM categories WHERE category_id = %s", (cat_id,))
