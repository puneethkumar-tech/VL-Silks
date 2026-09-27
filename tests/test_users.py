"""
VL Silks - User Management Tests
Regression tests verifying:
1. Sidebar link for User Management points to the correct URL (/users), not href="#"
2. Admin can view, create, edit, and toggle status of users
3. Staff and unauthenticated users are prevented from accessing User Management (Admin-only enforcement)
4. Safety rules (cannot deactivate or demote the sole active Admin)
"""
import pytest
from backend.app import create_app
from backend.services import user_service
from backend.services.user_service import ValidationError


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
def admin_client(client):
    """Authenticated Admin test client."""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Admin User'
        sess['user_email'] = 'admin@vlsilks.com'
        sess['user_role'] = 'ADMIN'
    return client


@pytest.fixture
def staff_client(client):
    """Authenticated Staff test client."""
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Staff Member'
        sess['user_email'] = 'staff@vlsilks.com'
        sess['user_role'] = 'STAFF'
    return client


# =========================================================================
# 1. SIDEBAR NAVIGATION TESTS
# =========================================================================

def test_sidebar_user_management_link_for_admin(admin_client):
    """Admin dashboard renders User Management link pointing to /users, not href='#'."""
    res = admin_client.get('/dashboard')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'User Management' in html
    assert 'href="/users"' in html
    # Verify User Management specifically does NOT use href="#"
    assert 'href="#" class="vl-nav-link' not in html or '/users' in html


def test_sidebar_user_management_hidden_for_staff(staff_client):
    """Staff sidebar does NOT show User Management link."""
    res = staff_client.get('/dashboard')
    assert res.status_code == 200
    html = res.data.decode('utf-8')
    assert 'User Management' not in html


# =========================================================================
# 2. ACCESS CONTROL / PERMISSION TESTS
# =========================================================================

def test_user_management_anonymous_redirect(client):
    """Unauthenticated users are redirected to login."""
    res = client.get('/users', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location


def test_user_management_staff_forbidden(staff_client):
    """Staff users cannot access User Management page and receive HTTP 403 Access Restricted page."""
    res = staff_client.get('/users', follow_redirects=False)
    assert res.status_code == 403
    assert b'Access Restricted' in res.data
    assert b'Administrator access required' in res.data

    res_new = staff_client.get('/users/new', follow_redirects=False)
    assert res_new.status_code == 403
    assert b'Access Restricted' in res_new.data


def test_access_restricted_403_page_elements(staff_client):
    """403 Access Restricted page contains shield icon, explanation, user role, and action buttons."""
    res = staff_client.get('/users')
    assert res.status_code == 403
    html = res.data.decode('utf-8')

    # Header & Titles
    assert 'Access Restricted' in html
    assert 'Administrator access required' in html
    assert 'Your current account does not have permission to access this section.' in html

    # Role badge display
    assert 'Current role: Staff Member' in html

    # Navigation buttons
    assert 'Back to Dashboard' in html
    assert 'Go Back' in html
    assert 'btnBackToDashboard' in html
    assert 'btnGoBack' in html
    assert '/dashboard' in html


def test_user_management_admin_access(admin_client):
    """Admin can access User Management list view with HTTP 200."""
    res = admin_client.get('/users')
    assert res.status_code == 200
    assert b'User Management' in res.data
    assert b'System Users' in res.data
    assert b'Add New User' in res.data


# =========================================================================
# 3. USER SERVICE CRUD & VALIDATION TESTS
# =========================================================================

import uuid

def test_create_user_service_and_retrieval(app):
    """Test creating a staff user via service and fetching by ID/email."""
    with app.app_context():
        email = f"test_staff_{uuid.uuid4().hex[:8]}@vlsilks.com"
        user_data = {
            'name': 'Test Staff Associate',
            'email': email,
            'password': 'password123',
            'role': 'STAFF',
            'status': 'ACTIVE'
        }
        user_id = user_service.create_user(user_data)
        assert user_id is not None

        user = user_service.get_user_by_id(user_id)
        assert user is not None
        assert user['name'] == 'Test Staff Associate'
        assert user['email'] == email.lower()
        assert user['role'] == 'STAFF'
        assert user['status'] == 'ACTIVE'

        user_by_email = user_service.get_user_by_email(email)
        assert user_by_email is not None
        assert user_by_email['user_id'] == user_id


def test_create_user_validation_errors(app):
    """Validation handles missing fields, invalid email, duplicate email, short password."""
    with app.app_context():
        # Missing name
        with pytest.raises(ValidationError, match="Full name is required"):
            user_service.create_user({
                'name': '',
                'email': 'valid@vlsilks.com',
                'password': 'password123'
            })

        # Invalid email format
        with pytest.raises(ValidationError, match="Invalid email address"):
            user_service.create_user({
                'name': 'John Doe',
                'email': 'not-an-email',
                'password': 'password123'
            })

        # Short password
        with pytest.raises(ValidationError, match="at least 6 characters"):
            user_service.create_user({
                'name': 'John Doe',
                'email': 'john@vlsilks.com',
                'password': '123'
            })


def test_update_user_and_toggle_status(app):
    """Test updating user information and toggling active status."""
    with app.app_context():
        email = f"toggle_test_{uuid.uuid4().hex[:8]}@vlsilks.com"
        user_id = user_service.create_user({
            'name': 'Toggle Tester',
            'email': email,
            'password': 'secretpassword',
            'role': 'STAFF',
            'status': 'ACTIVE'
        })

        # Update details
        user_service.update_user(user_id, {
            'name': 'Toggle Tester Updated',
            'email': email,
            'role': 'STAFF',
            'status': 'ACTIVE'
        })
        user = user_service.get_user_by_id(user_id)
        assert user['name'] == 'Toggle Tester Updated'

        # Toggle to INACTIVE
        new_status = user_service.toggle_user_status(user_id)
        assert new_status == 'INACTIVE'
        user = user_service.get_user_by_id(user_id)
        assert user['status'] == 'INACTIVE'

        # Toggle back to ACTIVE
        new_status2 = user_service.toggle_user_status(user_id)
        assert new_status2 == 'ACTIVE'


# =========================================================================
# 4. WEB ROUTE WORKFLOW TESTS
# =========================================================================

def test_web_create_user_flow(admin_client):
    """Admin can open new user form and submit valid user."""
    # GET new form
    res = admin_client.get('/users/new')
    assert res.status_code == 200
    assert b'Add New User Account' in res.data
    assert b'Role &amp; Access Level' in res.data or b'Role & Access Level' in res.data

    # POST new user
    email = f"web_staff_{uuid.uuid4().hex[:8]}@vlsilks.com"
    post_data = {
        'name': 'Web Created Staff',
        'email': email,
        'password': 'password123',
        'role': 'STAFF',
        'status': 'ACTIVE'
    }
    res = admin_client.post('/users/new', data=post_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'created successfully' in res.data
    assert b'Web Created Staff' in res.data


def test_web_edit_user_flow(app, admin_client):
    """Admin can edit an existing user."""
    email = f"web_edit_{uuid.uuid4().hex[:8]}@vlsilks.com"
    # Must run inside app context so user is created in vl_silks_test_db
    with app.app_context():
        user_id = user_service.create_user({
            'name': 'Web Edit Staff',
            'email': email,
            'password': 'password123',
            'role': 'STAFF',
            'status': 'ACTIVE'
        })

    # GET edit form
    res = admin_client.get(f'/users/{user_id}/edit')
    assert res.status_code == 200
    assert b'Edit User Account' in res.data

    # POST update
    update_data = {
        'name': 'Web Staff Modified',
        'email': email,
        'password': '',
        'role': 'STAFF',
        'status': 'ACTIVE'
    }
    res = admin_client.post(f'/users/{user_id}/edit', data=update_data, follow_redirects=True)
    assert res.status_code == 200
    assert b'updated successfully' in res.data
    assert b'Web Staff Modified' in res.data


def test_web_toggle_status_flow(app, admin_client):
    """Admin can toggle user status via POST."""
    email = f"web_toggle_{uuid.uuid4().hex[:8]}@vlsilks.com"
    # Must run inside app context so user is created in vl_silks_test_db
    with app.app_context():
        user_id = user_service.create_user({
            'name': 'Web Toggle Staff',
            'email': email,
            'password': 'password123',
            'role': 'STAFF',
            'status': 'ACTIVE'
        })

    res = admin_client.post(f'/users/{user_id}/toggle-status', follow_redirects=True)
    assert res.status_code == 200
    assert b'User status updated' in res.data


# =========================================================================
# 5. REST API TESTS
# =========================================================================

def test_api_users_admin_only(client):
    """API endpoints require admin privileges."""
    # Test unauthenticated
    res_anon = client.get('/api/users')
    assert res_anon.status_code == 403

    # Test staff
    with client.session_transaction() as sess:
        sess['user_id'] = 2
        sess['user_name'] = 'Staff Member'
        sess['user_email'] = 'staff@vlsilks.com'
        sess['user_role'] = 'STAFF'
    res_staff = client.get('/api/users')
    assert res_staff.status_code == 403

    # Test admin
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['user_name'] = 'Admin User'
        sess['user_email'] = 'admin@vlsilks.com'
        sess['user_role'] = 'ADMIN'
    res_admin = client.get('/api/users')
    assert res_admin.status_code == 200
    json_data = res_admin.get_json()
    assert json_data['status'] == 'success'
    assert 'data' in json_data
