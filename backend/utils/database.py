import os
import logging
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error, errorcode
from flask import current_app

logger = logging.getLogger('vl_silks.database')

def get_db_connection(config=None):
    """
    Creates and returns a MySQL database connection using credentials
    from Flask current_app config or the provided config object/dict.

    SSL/TLS (Aiven):
        Set the MYSQL_SSL_CA environment variable to the path of the Aiven
        CA certificate file (ca.pem downloaded from the Aiven console).
        When set, all connections use TLS with certificate verification.
        When absent, plain connections are used (local development).
    """
    if config is None and current_app:
        cfg = current_app.config
        host = cfg.get('DB_HOST', '127.0.0.1')
        port = int(cfg.get('DB_PORT', 3306))
        user = cfg.get('DB_USER', 'root')
        password = cfg.get('DB_PASSWORD', '')
        database = cfg.get('DB_NAME', 'vl_silks_db')
        is_testing = cfg.get('TESTING', False)
    elif isinstance(config, dict):
        host = config.get('DB_HOST', '127.0.0.1')
        port = int(config.get('DB_PORT', 3306))
        user = config.get('DB_USER', 'root')
        password = config.get('DB_PASSWORD', '')
        database = config.get('DB_NAME', 'vl_silks_db')
        is_testing = config.get('TESTING', False)
    elif hasattr(config, 'DB_HOST'):
        host = getattr(config, 'DB_HOST')
        port = int(getattr(config, 'DB_PORT', 3306))
        user = getattr(config, 'DB_USER', 'root')
        password = getattr(config, 'DB_PASSWORD', '')
        database = getattr(config, 'DB_NAME', 'vl_silks_db')
        is_testing = getattr(config, 'TESTING', False)
    else:
        host = os.getenv('DB_HOST', '127.0.0.1')
        port = int(os.getenv('DB_PORT', 3306))
        user = os.getenv('DB_USER', 'root')
        password = os.getenv('DB_PASSWORD', '')
        database = os.getenv('DB_NAME', 'vl_silks_db')
        is_testing = False

    # Safety assertion: if testing, ensure database is never the production/dev DB
    if is_testing:
        from backend.config import TestingConfig
        verified_test_db = TestingConfig.resolve_test_db_name()
        if database != verified_test_db:
            raise RuntimeError(
                f"Database Isolation Error: Testing context attempted connection to '{database}' instead of isolated test DB '{verified_test_db}'."
            )

    # ---------------------------------------------------------------------------
    # SSL/TLS Configuration (Aiven MySQL)
    # ---------------------------------------------------------------------------
    # Set MYSQL_SSL_CA to the path of the Aiven CA certificate file (ca.pem).
    # This file is downloaded from the Aiven console and must be made available
    # to the running process (e.g., committed to the repo or uploaded to Render).
    # When MYSQL_SSL_CA is not set, plain connections are used (local dev).
    # ---------------------------------------------------------------------------
    ssl_ca_path = os.getenv('MYSQL_SSL_CA', '').strip()

    if ssl_ca_path:
        # Remote/cloud connection with TLS verification (Aiven)
        connect_kwargs = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            use_unicode=True,
            autocommit=False,
            connection_timeout=30,
            ssl_ca=ssl_ca_path,
            ssl_verify_cert=True,
            ssl_disabled=False,
        )
    else:
        # Local development connection — no SSL required
        connect_kwargs = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            use_unicode=True,
            autocommit=False,
            connection_timeout=30,
        )

    try:
        connection = mysql.connector.connect(**connect_kwargs)
        return connection
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("Database connection failed: Invalid user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            logger.error(f"Database '{database}' does not exist")
        else:
            logger.error(f"Database error: {err}")
        raise

@contextmanager
def get_db_cursor(commit=False, dictionary=True, config=None):
    """
    Context manager that yields a cursor and safely handles commit, rollback, and cleanup.
    
    Usage:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT INTO ...", (val1, val2))
    """
    connection = get_db_connection(config)
    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield cursor
        if commit:
            connection.commit()
    except Exception as e:
        if commit:
            connection.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        cursor.close()
        connection.close()

def query_db(query, args=(), one=False, dictionary=True, config=None):
    """
    Helper function to execute read-only queries with parameters.
    """
    with get_db_cursor(commit=False, dictionary=dictionary, config=config) as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True, config=None):
    """
    Helper function to execute write queries (INSERT, UPDATE, DELETE) with parameters.
    Returns (rowcount, lastrowid).
    """
    with get_db_cursor(commit=commit, dictionary=True, config=config) as cursor:
        cursor.execute(query, args)
        return cursor.rowcount, cursor.lastrowid
