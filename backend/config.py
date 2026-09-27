import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env in project root (no-op on Render where env vars are set directly)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

logger = logging.getLogger('vl_silks.config')


class Config:
    """Base configuration loaded from environment variables.

    All sensitive values MUST be supplied as environment variables.
    Default values are safe for local development only.
    """
    SECRET_KEY = os.getenv('SECRET_KEY', 'vl-silks-default-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')

    # Safe default: DEBUG is OFF unless explicitly enabled.
    # Local dev: set FLASK_DEBUG=1 in .env to enable.
    # Production (Render): set FLASK_DEBUG=0 (or omit entirely).
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'

    # Database Configuration — all values read from environment
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    DB_NAME = os.getenv('DB_NAME', 'vl_silks_db')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # Brand Configuration
    BRAND_NAME = "VL Silks"
    BRAND_TAGLINE = "TRADITION MEETS FASHION"
    BRAND_PRIMARY_COLOR = "#8B0000"
    BRAND_SECONDARY_COLOR = "#D4AF37"
    BRAND_BG_COLOR = "#FFF8E1"
    BRAND_TEXT_COLOR = "#333333"

    # Uploads / Assets
    UPLOAD_FOLDER = BASE_DIR / 'uploads'


def validate_production_config():
    """
    Validates that the running configuration is safe for production.
    Called by create_app() when FLASK_ENV=production.

    Raises RuntimeError with a descriptive message if any critical
    misconfiguration is detected. Never prints or logs secret values.
    """
    errors = []

    # 1. Must not run with DEBUG enabled in production
    if os.getenv('FLASK_DEBUG', '0') == '1':
        errors.append("FLASK_DEBUG=1 is set — DEBUG mode must be disabled in production (set FLASK_DEBUG=0).")

    # 2. SECRET_KEY must be explicitly set and not the known default placeholder
    secret_key = os.getenv('SECRET_KEY', '')
    known_weak_defaults = {
        '',
        'vl-silks-default-secret-key-change-in-production',
        'vl-silks-super-secret-key-change-in-production',
    }
    if not secret_key or secret_key in known_weak_defaults:
        errors.append("SECRET_KEY is not set or is using the insecure default value. Set a strong random SECRET_KEY environment variable on Render.")

    # 3. Required database connection vars
    missing_db_vars = [v for v in ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD') if not os.getenv(v)]
    if missing_db_vars:
        errors.append(f"Missing required database environment variables: {', '.join(missing_db_vars)}")

    # 4. DB_HOST must not be localhost/127.0.0.1 in production
    db_host = os.getenv('DB_HOST', '')
    if db_host in ('127.0.0.1', 'localhost', ''):
        errors.append(f"DB_HOST is '{db_host}' — production must connect to a remote database (Aiven), not localhost.")

    # 5. TEST_DB_NAME must NOT be set in production (prevents test/prod confusion)
    if os.getenv('TEST_DB_NAME'):
        errors.append("TEST_DB_NAME is set in the production environment. Remove this variable from Render — it should only exist in local/CI environments.")

    if errors:
        error_list = '\n  - '.join(errors)
        raise RuntimeError(
            f"Production configuration validation failed. Fix the following issues:\n  - {error_list}"
        )

    logger.info("Production configuration validated successfully.")


class DevelopmentConfig(Config):
    """Local development configuration — DEBUG enabled."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration for Render deployment.

    All secrets and DB credentials MUST be supplied as Render environment variables.
    This class must never fall back to development defaults for any security-sensitive setting.
    """
    DEBUG = False

    # Secure session cookies — required for HTTPS (Render provides HTTPS automatically)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    TESTING = True
    DEBUG = True

    @staticmethod
    def resolve_test_db_name():
        """
        Explicitly resolves and validates the isolated test database name.
        Guarantees that tests can never run against or fall back to the development/production DB.
        """
        test_db = os.getenv('TEST_DB_NAME')
        dev_db = os.getenv('DB_NAME', 'vl_silks_db')

        if not test_db or not test_db.strip():
            raise RuntimeError(
                "Configuration Error: 'TEST_DB_NAME' environment variable is required for TestingConfig. "
                "Tests cannot execute without an isolated test database."
            )

        if test_db.strip() == dev_db.strip():
            raise RuntimeError(
                f"Configuration Error: 'TEST_DB_NAME' ('{test_db}') cannot match the development/production database '{dev_db}'. "
                "An isolated test database is required to prevent data contamination."
            )

        return test_db.strip()

    # DB_NAME is set from TEST_DB_NAME
    DB_NAME = os.getenv('TEST_DB_NAME')


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}
