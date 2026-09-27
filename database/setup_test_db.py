"""
VL Silks – Test Database Setup Script
Creates and provisions the isolated test database (vl_silks_test_db)
using database/schema.sql and database/seed.sql.

Guarantees complete isolation from the production/demo database (vl_silks_db).
"""

import os
import sys
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

sys.path.insert(0, str(BASE_DIR))
from backend.config import Config, TestingConfig


def setup_test_database(seed=True):
    """
    Creates and sets up the isolated test database.
    """
    test_db = TestingConfig.resolve_test_db_name()
    dev_db = os.getenv('DB_NAME', 'vl_silks_db')

    if test_db == dev_db:
        raise RuntimeError(
            f"FATAL: Test DB name '{test_db}' matches production DB name '{dev_db}'. Setup aborted."
        )

    host = os.getenv('DB_HOST', '127.0.0.1')
    port = int(os.getenv('DB_PORT', 3306))
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')

    print(f"Connecting to MySQL server at {host}:{port} as user '{user}'...")
    server_conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password
    )
    server_cur = server_conn.cursor()

    print(f"Creating isolated test database '{test_db}' (if not exists)...")
    server_cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{test_db}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    server_conn.close()

    print(f"Applying schema.sql to '{test_db}'...")
    test_conn = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=test_db
    )
    test_cur = test_conn.cursor()

    schema_file = BASE_DIR / 'database' / 'schema.sql'
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Execute schema statements
    for statement in schema_sql.split(';'):
        stmt = statement.strip()
        if stmt:
            test_cur.execute(stmt)

    if seed:
        print(f"Applying seed.sql to '{test_db}'...")
        seed_file = BASE_DIR / 'database' / 'seed.sql'
        with open(seed_file, 'r', encoding='utf-8') as f:
            seed_sql = f.read()

        for statement in seed_sql.split(';'):
            stmt = statement.strip()
            if stmt:
                test_cur.execute(stmt)

    test_conn.commit()

    # Verify tables
    test_cur.execute("SHOW TABLES")
    tables = [list(r.values())[0] if isinstance(r, dict) else r[0] for r in test_cur.fetchall()]
    print(f"SUCCESS: Test database '{test_db}' successfully initialized with {len(tables)} tables.")
    test_conn.close()
    return test_db


if __name__ == '__main__':
    setup_test_database()
