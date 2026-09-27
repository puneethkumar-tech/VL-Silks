"""
VL Silks – Test Database Isolation & Safety Verification
Verifies:
  1. TestingConfig strictly requires TEST_DB_NAME environment variable.
  2. TestingConfig rejects any configuration where TEST_DB_NAME equals DB_NAME.
  3. TestingConfig never silently falls back to vl_silks_db.
  4. Test runtime connections only ever connect to the isolated test database.
  5. Configuration error messages do not leak database credentials.
"""

import pytest
import os
from backend.app import create_app
from backend.config import Config, DevelopmentConfig, TestingConfig
from backend.utils.database import get_db_connection, query_db


def test_testing_config_requires_test_db_name_env_var(monkeypatch):
    """Test: When TEST_DB_NAME is unset, TestingConfig and create_app('testing') raise RuntimeError."""
    monkeypatch.delenv('TEST_DB_NAME', raising=False)
    
    with pytest.raises(RuntimeError) as exc_info:
        TestingConfig.resolve_test_db_name()
    assert "TEST_DB_NAME" in str(exc_info.value)
    assert "Configuration Error" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info2:
        create_app('testing')
    assert "TEST_DB_NAME" in str(exc_info2.value)


def test_testing_config_rejects_matching_dev_db_name(monkeypatch):
    """Test: When TEST_DB_NAME equals the development/production DB name, RuntimeError is raised."""
    dev_db = os.getenv('DB_NAME', 'vl_silks_db')
    monkeypatch.setenv('TEST_DB_NAME', dev_db)

    with pytest.raises(RuntimeError) as exc_info:
        TestingConfig.resolve_test_db_name()
    assert "cannot match the development/production database" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info2:
        create_app('testing')
    assert "cannot match the development/production database" in str(exc_info2.value)


def test_test_db_name_is_distinct_from_development_db():
    """Test: Verified that isolated test DB name is different from development DB."""
    test_db = TestingConfig.resolve_test_db_name()
    dev_db = DevelopmentConfig.DB_NAME
    assert test_db != dev_db
    assert test_db == "vl_silks_test_db"
    assert dev_db == "vl_silks_db"


def test_testing_app_context_connects_only_to_test_db():
    """Test: Live database query inside testing context is confirmed to hit vl_silks_test_db."""
    app = create_app('testing')
    with app.app_context():
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT DATABASE() AS active_db")
        row = cur.fetchone()
        cur.close()
        conn.close()

        assert row is not None
        assert row['active_db'] == 'vl_silks_test_db'
        assert row['active_db'] != 'vl_silks_db'


def test_no_credentials_exposed_in_config_errors(monkeypatch):
    """Test: Configuration error messages do not leak database passwords or secrets."""
    monkeypatch.delenv('TEST_DB_NAME', raising=False)
    
    try:
        TestingConfig.resolve_test_db_name()
    except RuntimeError as e:
        err_msg = str(e)
        assert "password" not in err_msg.lower()
        assert "Venkata@" not in err_msg
        assert "secret" not in err_msg.lower()
