# System Architecture
## VL Silks - Garment Shop Inventory, Sales & Credit Management System
---
## 1. Architectural Overview
VL Silks is engineered as a robust, modular **Three-Tier Web Application** adhering to the **Model-Template-Service/Route** pattern:
1. **Presentation Tier (Client / Frontend):**
   - Responsive HTML5, Vanilla CSS3, Bootstrap 5 UI framework.
   - Dynamic interactivity via Vanilla JavaScript (Fetch API, DOM manipulation, POS calculations).
   - Chart.js for interactive dashboard data visualizations.
   - Jinja2 server-side templating engine with reusable layout inheritance.
2. **Application Tier (Server / Backend):**
   - Python 3.12+ with Flask web framework.
   - Modular Flask Blueprints for clean domain separation.
   - Dedicated Service Layer isolating business logic, validation, and database operations.
   - ReportLab PDF generation engine for high-fidelity statement printing.
   - Role-Based Access Control (RBAC) decorators (`@login_required`, `@admin_required`).
3. **Data Tier (Persistence / Database):**
   - MySQL 8.x Relational Database Management System (InnoDB Engine).
   - 15 fully normalized tables with primary keys, foreign keys, uniqueness constraints, and check constraints (`stock_quantity >= 0`).
   - Atomic ACID transactions (`BEGIN`, `COMMIT`, `ROLLBACK`) for multi-step financial and stock workflows.
---
## 2. Architectural Diagram
```
+---------------------------------------------------------------------------------+
|                               PRESENTATION TIER                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         Web Browser (Client)                            |   |
|   |  - HTML5 / Bootstrap 5 / Custom CSS (VL Silks Maroon & Gold Theme)      |   |
|   |  - Jinja2 Templates (base.html, dashboard, pos, credit, reports, etc.)  |   |
|   |  - Vanilla JS (POS cart, real-time calculations, AJAX modal handlers)   |   |
|   |  - Chart.js (Monthly sales trends, Category breakdown charts)           |   |
|   +-------------------------------------------------------------------------+   |
+----------------------------------------+----------------------------------------+
                                         | HTTP / HTTPS (JSON & Form Requests)
                                         v
+---------------------------------------------------------------------------------+
|                               APPLICATION TIER                                  |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                        Flask Application Factory                        |   |
|   |                     backend/app.py (create_app())                       |   |
|   |                     Configuration: backend/config.py                    |   |
|   +------------------------------------+------------------------------------+   |
|                                        |                                        |
|   +------------------------------------v------------------------------------+   |
|   |                         Authentication & RBAC                           |   |
|   |        @login_required (Staff/Admin)  |  @admin_required (Admin Only)   |   |
|   |        Flask Secure Session Management  |  Werkzeug Scrypt Hashing      |   |
|   +------------------------------------+------------------------------------+   |
|                                        |                                        |
|   +------------------------------------v------------------------------------+   |
|   |                         Flask Blueprints (Routes)                       |   |
|   |   auth_bp        dashboard_bp   products_bp    categories_bp            |   |
|   |   suppliers_bp   purchases_bp   inventory_bp   sales_bp (POS)           |   |
|   |   customers_bp   credit_bp      returns_bp     reports_bp               |   |
|   |   pdf_bp         health_bp                                              |   |
|   +------------------------------------+------------------------------------+   |
|                                        |                                        |
|   +------------------------------------v------------------------------------+   |
|   |                          Dedicated Service Layer                        |   |
|   |   auth_service.py       product_service.py     category_service.py      |   |
|   |   supplier_service.py   purchase_service.py    inventory_service.py     |   |
|   |   sale_service.py       customer_service.py    credit_service.py        |   |
|   |   return_service.py     report_service.py      dashboard_service.py     |   |
|   |   pdf_service.py (ReportLab Generator)                                  |   |
|   |                                                                         |   |
|   |   * Pure Decimal arithmetic (2 decimal places)                          |   |
|   |   * Explicit Transaction Control (commit / rollback)                    |   |
|   |   * Parameterized SQL Execution via mysql-connector-python              |   |
|   +------------------------------------+------------------------------------+   |
+----------------------------------------+----------------------------------------+
                                         | SQL Queries (mysql-connector-python)
                                         v
+---------------------------------------------------------------------------------+
|                                  DATA TIER                                      |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         MySQL 8.x (InnoDB Engine)                       |   |
|   |                                                                         |   |
|   |   Core Catalog:     categories, products, product_variants              |   |
|   |   Procurement:      suppliers, purchases, purchase_items                |   |
|   |   Sales & Billing:  customers, sales, sale_items, payments              |   |
|   |   Credit & Stock:   credit_transactions, stock_movements                |   |
|   |   After-Sales:      returns, return_items                               |   |
|   |   Administration:   users                                               |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```
---
## 3. Key Design Patterns & Principles
1. **Application Factory Pattern (`create_app`):**
   Encapsulates Flask application creation and blueprint registration, supporting modular test environments (`TestingConfig`) and production environments (`DevelopmentConfig` / `ProductionConfig`).
2. **Service Layer Pattern:**
   Route handlers act as thin controllers responsible solely for request deserialization, parameter validation, and response serialization. All business calculations, database queries, and transactional boundaries are isolated in `backend/services/`.
3. **Financial Precision Guarantee:**
   All monetary calculations (unit prices, tax, discounts, line totals, balances, profits) use Python's `decimal.Decimal` module quantized to two decimal places (`Decimal('0.01')`), eliminating floating-point rounding errors.
4. **Transactional ACID Boundaries:**
   Operations affecting multiple tables (e.g., POS checkout, inward purchase receipt, returns/exchanges, credit settlement) execute within explicit transaction contexts with `conn.begin()`, `conn.commit()`, and `conn.rollback()` error trapping.
