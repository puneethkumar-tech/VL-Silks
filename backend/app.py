import os
from pathlib import Path
from flask import Flask, render_template, jsonify
from backend.config import config_by_name, Config, validate_production_config
from backend.routes.health import health_bp
from backend.routes.auth import auth_bp
from backend.routes.dashboard import dashboard_bp
from backend.routes.products import products_bp
from backend.routes.categories import categories_bp
from backend.routes.suppliers import suppliers_bp
from backend.routes.purchases import purchases_bp
from backend.routes.inventory import inventory_bp
from backend.routes.sales import sales_bp
from backend.routes.customers import customers_bp
from backend.routes.credit import credit_bp
from backend.routes.pdf import pdf_bp
from backend.routes.returns import returns_bp
from backend.routes.reports import reports_bp
from backend.routes.users import users_bp

def create_app(config_name=None):
    """
    Application factory for VL Silks management system.
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    # Validate production configuration before anything else starts.
    # Raises RuntimeError immediately if critical env vars are missing or misconfigured.
    if config_name == 'production':
        validate_production_config()

    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / 'templates'),
        static_folder=str(Path(__file__).parent / 'static')
    )

    # Load configuration
    cfg_class = config_by_name.get(config_name, Config)
    app.config.from_object(cfg_class)

    # Enforce strict test database isolation for test environments
    if config_name == 'testing' or app.config.get('TESTING'):
        from backend.config import TestingConfig
        test_db = TestingConfig.resolve_test_db_name()
        app.config['DB_NAME'] = test_db

    # Register Brand Context Processor for templates
    @app.context_processor
    def inject_brand():
        return {
            'BRAND_NAME': app.config.get('BRAND_NAME', 'VL Silks'),
            'BRAND_TAGLINE': app.config.get('BRAND_TAGLINE', 'TRADITION MEETS FASHION'),
            'BRAND_PRIMARY_COLOR': app.config.get('BRAND_PRIMARY_COLOR', '#8B0000'),
            'BRAND_SECONDARY_COLOR': app.config.get('BRAND_SECONDARY_COLOR', '#D4AF37'),
            'BRAND_BG_COLOR': app.config.get('BRAND_BG_COLOR', '#FFF8E1'),
            'BRAND_TEXT_COLOR': app.config.get('BRAND_TEXT_COLOR', '#333333'),
        }

    # Register Custom Template Filters
    @app.template_filter('currency')
    def currency_filter(value):
        try:
            return f"₹{float(value):,.2f}"
        except (ValueError, TypeError):
            return f"₹{value}"

    # Register Blueprints
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(credit_bp)
    app.register_blueprint(pdf_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)

    # Global Error Handlers
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', True))
