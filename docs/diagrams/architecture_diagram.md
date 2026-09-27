# Architecture Diagram

## VL Silks - Three-Tier System Architecture Diagram

```text
+---------------------------------------------------------------------------------+
|                               PRESENTATION TIER                                 |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         Web Browser (Client)                            |   |
|   |  - Responsive HTML5 / Bootstrap 5 / VL Silks Maroon & Gold Theme        |   |
|   |  - Jinja2 Templates (base.html, dashboard, pos, credit, reports, etc.)  |   |
|   |  - Vanilla JS (Cart management, real-time totals, dynamic DOM updates)  |   |
|   |  - Chart.js (6-Month Sales Trend & Category Distribution Visualizations)|   |
|   +-------------------------------------------------------------------------+   |
+----------------------------------------+----------------------------------------+
                                         | HTTP / HTTPS Requests (JSON & Forms)
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
|   |   pdf_service.py (ReportLab PDF Generation)                             |   |
|   |                                                                         |   |
|   |   * Pure Decimal arithmetic (2 decimal places)                          |   |
|   |   * Explicit Transaction Control (commit / rollback)                    |   |
|   |   * Parameterized SQL Execution via mysql-connector-python              |   |
|   +------------------------------------+------------------------------------+   |
+----------------------------------------+----------------------------------------+
                                         | Parameterized SQL Queries (mysql-connector-python)
                                         v
+---------------------------------------------------------------------------------+
|                                  DATA TIER                                      |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                         MySQL 8.x (InnoDB Engine)                       |   |
|   |                                                                         |   |
|   |   Catalog:       categories, products, product_variants                 |   |
|   |   Procurement:   suppliers, purchases, purchase_items                   |   |
|   |   Sales & POS:   customers, sales, sale_items, payments                 |   |
|   |   Credit & Stock:credit_transactions, stock_movements                   |   |
|   |   After-Sales:   returns, return_items                                  |   |
|   |   Access:        users                                                  |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```
