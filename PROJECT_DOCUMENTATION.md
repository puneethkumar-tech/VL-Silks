# VL Silks - Comprehensive Project Documentation

## Garment Shop Inventory, Sales & Credit Management System
**College DBMS & Software Engineering Project Documentation**

---

## 1. Project Abstract

Small and medium-scale garment shops in India traditionally rely on handwritten ledgers, paper invoices, and physical stock registers to manage their day-to-day operations. This manual approach introduces several serious problems: stock levels become inaccurate when entries are missed or made incorrectly, billing takes excessive time when product details must be looked up manually, customer credit (locally referred to as Udhaar) is tracked in separate notebooks that can be lost or miscalculated, and generating any meaningful business summary requires hours of manual reconciliation.

**VL Silks** is a comprehensive web-based Garment Shop Inventory, Sales, and Credit Management System developed to solve these problems for a real-world Indian silk garment retail business. The system replaces all manual paper-based processes with a centralized, database-backed digital application.

The system manages a complete garment catalog with products and their size/color variants, each uniquely identified by SKU and optional barcode. Stock levels are maintained in real time through an automated inventory movement audit trail that records every inward purchase, outward sale, customer return, damaged write-off, and manual correction. A Purchase Management module handles inward supplier invoices, automatically increasing stock on confirmation.

The Point-of-Sale (POS) billing module allows staff to create itemized customer invoices supporting multiple payment methods — Cash, UPI, Card, Credit (Udhaar), and Split payments. Financial totals are computed server-side using Python Decimal arithmetic to guarantee accuracy. The Customer Management module maintains customer profiles with contact information, credit limits, and complete purchase histories.

The Credit/Udhaar Management system maintains an authoritative transactional ledger (`credit_transactions`) for every customer. Outstanding balances are computed directly from ledger entries — CREDIT_SALE debits and PAYMENT/RETURN_REFUND credits — making the system the single source of truth for all outstanding receivables. Customers can make partial or full settlements, and official credit statements can be exported as professionally branded A4 PDF documents using the ReportLab library.

A Returns and Exchanges module allows staff to process garment returns against original invoices. The system supports RESTOCKABLE and DAMAGED condition classifications, Cash and Credit refund types, and full garment exchange workflows with price difference handling. All return operations are atomic — they either complete fully or roll back completely.

The Dashboard provides real-time business KPIs including today's sales, this month's revenue, total credit outstanding, low-stock alerts, top-selling products, monthly trend charts, and category distribution charts. A dedicated Reports module generates Sales Reports, Purchase Reports, Inventory Valuation Reports, Credit Aging Reports, and Profit Reports, all exportable to CSV.

The system is built on a Flask (Python) backend with a MySQL relational database containing 15 normalized tables. The frontend uses HTML, CSS, JavaScript, and Bootstrap, rendered via Jinja2 templates. Role-based access control distinguishes Administrator users from Staff users, with Admin-only restrictions on sensitive operations. All database interactions use parameterized queries, all monetary values use Decimal arithmetic, and all multi-step operations execute within atomic database transactions with rollback protection.

---

## 2. Technical Stack & Specifications

- **Backend Framework:** Python 3.12+ with Flask
- **Database Engine:** MySQL 8.x (InnoDB Engine, utf8mb4 charset, utf8mb4_unicode_ci collation)
- **Frontend / Templating:** HTML5, Vanilla CSS3 (Maroon `#8B0000` & Gold `#D4AF37` Brand Palette), Bootstrap 5, Jinja2, Vanilla JS, Chart.js
- **Document Generation:** ReportLab (Server-side PDF generation for A4 customer credit statements)
- **Database Driver:** mysql-connector-python (100% Parameterized queries with `%s` tuple substitution)
- **Password Security:** Werkzeug Scrypt memory-hard hashing
- **Testing Framework:** Pytest (390 tests collected: 388 passed, 2 skipped across 16 test modules)

---

## 3. System Architecture

The application follows a clean **Three-Tier Architecture** utilizing the **Model-Template-Service** design pattern:

```text
+-------------------------------------------------------------------------+
|                            PRESENTATION TIER                            |
|  - HTML5 / Bootstrap 5 / Jinja2 Templates (base.html, POS, Reports)     |
|  - Chart.js interactive charts / Vanilla JavaScript client logic        |
+------------------------------------+------------------------------------+
                                     | HTTP Requests
                                     v
+-------------------------------------------------------------------------+
|                            APPLICATION TIER                             |
|  - Flask Application Factory (backend/app.py -> create_app())           |
|  - Authentication & RBAC Decorators (@login_required, @admin_required)  |
|  - Blueprints: auth, dashboard, products, categories, suppliers,        |
|    purchases, inventory, sales, customers, credit, returns, reports, pdf|
|  - Service Layer (backend/services/): 100% business logic & Decimal math|
|  - ReportLab PDF Generation (backend/services/pdf_service.py)           |
+------------------------------------+------------------------------------+
                                     | Parameterized SQL
                                     v
+-------------------------------------------------------------------------+
|                                DATA TIER                                |
|  - MySQL 8.x InnoDB Relational Database (15 3NF Normalized Tables)      |
|  - ACID Transactions (BEGIN / COMMIT / ROLLBACK)                        |
|  - Table Constraints (FK RESTRICT/CASCADE/SET NULL, CHECK stock >= 0)   |
+-------------------------------------------------------------------------+
```

---

## 4. Database Schema (15 Tables) & Normalization

### 4.1 Schema Overview
The database schema consists of **15 normalized tables** in `vl_silks_db`:

1. `users` — System user accounts and role-based permissions (`ADMIN`, `STAFF`).
2. `categories` — Product categories (Silk Sarees, Dhotis, Kurtis, etc.).
3. `products` — Base garment definitions (brand, material, description).
4. `product_variants` — Specific SKU/Barcode variants with size, color, cost price, selling price, and stock count (`CHECK stock_quantity >= 0`).
5. `suppliers` — Fabric suppliers and weavers master registry.
6. `purchases` — Inward supplier procurement bills and invoices.
7. `purchase_items` — Line items for inward purchase bills.
8. `customers` — Customer registry with contact details and authorized credit limits.
9. `sales` — Customer sales invoices (`SALE-YYYY-NNNN`), totals, and payment status.
10. `sale_items` — Itemized garments sold per invoice.
11. `payments` — Counter receipts and Udhaar settlement records.
12. `credit_transactions` — Authoritative running Udhaar ledger (`CREDIT_SALE`, `PAYMENT`, `RETURN_REFUND`).
13. `stock_movements` — Complete inventory movement audit trail (`PURCHASE`, `SALE`, `CUSTOMER_RETURN`, `DAMAGE`, `ADJUSTMENT`).
14. `returns` — Customer garment return and exchange transactions.
15. `return_items` — Returned garment items with condition checks (`RESTOCKABLE`, `DAMAGED`).

### 4.2 Normalization Summary
- **1NF:** Atomic scalar attributes throughout; no delimited strings or repeating arrays.
- **2NF:** All 15 tables utilize single-column surrogate primary keys (`AUTO_INCREMENT INT`), completely avoiding partial dependencies.
- **3NF:** Transitive dependencies eliminated by separating categories, base products, variants, and customer profiles into independent relational entities.
- **Audit Snapshots:** Invoice totals (`total_amount`, `balance_amount`) and line prices (`unit_price`) represent immutable historical transaction facts preserved for legal auditability.

---

## 5. Core Business Subsystems & Workflows

### 5.1 Point of Sale (POS) Billing
- Fast product/variant search and barcode integration.
- Supports 5 payment methods: `CASH`, `UPI`, `CARD`, `CREDIT` (Udhaar), and `SPLIT`.
- Enforces customer credit limit checks before authorizing Udhaar checkout.
- Atomically generates invoices, deducts inventory, records `stock_movements`, and appends credit debits.

### 5.2 Customer Credit / Udhaar Management
- Authoritative running transactional ledger (`credit_transactions`).
- Outstanding balance is computed directly from ledger records.
- Settlement payment recording with automated overpayment protection.
- Downloadable branded A4 PDF Credit Statements generated via ReportLab.

### 5.3 Returns & Garment Exchanges
- Item condition verification: `RESTOCKABLE` (shelf stock restored) vs `DAMAGED` (stock not restored, damaged audit log recorded).
- Refund modes: `CASH` or `CREDIT_ADJUSTMENT` (`RETURN_REFUND` in Udhaar ledger).
- Atomic garment exchange: returns old variant, issues replacement variant, and reconciles price difference in a single database transaction.

### 5.4 Inventory Movement Auditing
- Immutable audit log capturing all 5 movement reasons: `PURCHASE`, `SALE`, `CUSTOMER_RETURN`, `DAMAGE`, `ADJUSTMENT`.
- Stock quantities strictly protected against negative values at both application and MySQL database constraint levels.

### 5.5 Business Reports & CSV Export
- **Sales Report:** Revenue, discounts, taxes, and payment method distribution.
- **Purchase Report:** Procurement volume, costs, and supplier payables.
- **Inventory Valuation Report:** Stock asset valuation at cost vs retail price.
- **Credit Aging Report:** Receivables bucketed into 0-30, 31-60, 61-90, 90+ day schedules.
- **Gross Profit Report:** Itemized profit margin per garment variant (`Selling Price - Cost Price`).
- All reports feature one-click CSV export and printable formats.

---

## 6. Security Model & Data Integrity

1. **Role-Based Access Control (RBAC):**
   - `@login_required` protects all operational pages.
   - `@admin_required` restricts destructive and configuration operations (catalog creation, stock adjustments, supplier registration, financial profit reports).
2. **SQL Injection Prevention:** 100% parameterized SQL execution with `mysql-connector-python` placeholders (`%s`). Zero string interpolation.
3. **Password Security:** Salted memory-hard Scrypt hashing via `werkzeug.security`.
4. **Financial Arithmetic:** Pure Python `decimal.Decimal` arithmetic quantized to 2 decimal places (`0.01`) across all services. Zero floating-point drift.
5. **ACID Transactions:** Explicit `conn.begin()` ... `conn.commit()` blocks with rollback error trapping for all multi-table mutations.

---

## 7. Verification & Automated Test Suite

### 7.1 Pytest Automated Suite (390 Tests Collected across 16 Modules)
- **Total Test Cases:** **390 tests collected: 388 passed, 2 skipped** across **16 test modules**.
- **Execution Status:** 388 passed, 2 skipped (0 failures, 0 errors).
- **Test Modules Breakdown (16 Test Files):**
  1. `tests/test_phase1.py` (7 tests: 5 passed, 2 skipped) — Application factory, `/api/health`, DB connectivity, 15 tables verification
  2. `tests/test_categories.py` (11 tests) — Category CRUD, uniqueness validation, status toggling
  3. `tests/test_products.py` (23 tests) — Product & variant catalog, SKU uniqueness, stock validation
  4. `tests/test_suppliers.py` (22 tests) — Supplier master CRUD, phone/GST validation, purchase history
  5. `tests/test_purchases.py` (33 tests) — Inward purchase invoice entry, stock increment, movement audit
  6. `tests/test_inventory.py` (40 tests) — Real-time stock levels, movement history, manual adjustments, alerts
  7. `tests/test_sales.py` (19 tests) — POS checkout, line discounts, payment methods, stock deduction
  8. `tests/test_customers.py` (37 tests) — Customer profile CRUD, phone search, credit limits, purchase history
  9. `tests/test_credit.py` (36 tests) — Udhaar ledger, balance calculation, settlement payments, overpayment rejection
  10. `tests/test_pdf.py` (21 tests) — ReportLab PDF credit statement generation, layout, multi-page pagination
  11. `tests/test_returns.py` (63 tests) — Returns, exchanges, restockable vs damaged items, invoice search widget
  12. `tests/test_dashboard.py` (12 tests) — KPI computations, monthly trend aggregations, top product rankings
  13. `tests/test_reports.py` (38 tests) — Sales, Purchase, Inventory Valuation, Credit Aging, Profit reports, CSV exports
  14. `tests/test_users.py` (13 tests) — User management, role access control, password updates
  15. `tests/test_database_isolation.py` (5 tests) — Database isolation enforcement and TestingConfig guards
  16. `tests/test_phase16_verification.py` (10 tests) — End-to-end integration cycles and data invariant validation

### 7.2 Playwright End-to-End (E2E) Browser QA
- **E2E Test Results:** **13 passed, 0 failed, 0 skipped, 0 console errors, 0 failed network requests**.
- **Coverage:** Full user journeys across Authentication, Dashboard, Products, Categories, Inventory, Purchases, POS, Customers, Credit/PDF, Returns, Reports, RBAC (Admin vs Staff), and Responsive UI across Desktop, Laptop, and Mobile Chromium viewports.

---

## 8. Complete Documentation Directory Index (`docs/`)

For in-depth analysis and technical details, refer to the individual documentation files:

1. **[Project Abstract](docs/PROJECT_ABSTRACT.md)**
2. **[Problem Statement](docs/PROBLEM_STATEMENT.md)**
3. **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)**
4. **[ER Diagram](docs/ER_DIAGRAM.md)**
5. **[Data Flow Diagram](docs/DFD.md)**
6. **[Database Schema](docs/DATABASE_SCHEMA.md)**
7. **[Database Normalization](docs/NORMALIZATION.md)**
8. **[Module Specifications](docs/MODULES.md)**
9. **[Security Architecture](docs/SECURITY.md)**
10. **[Testing & QA](docs/TESTING.md)**
11. **[System Workflows](docs/WORKFLOWS.md)**
12. **[Comprehensive Viva Voce Guide (60 Q&A)](docs/VIVA_QA.md)**
13. **[Architecture Diagram Source](docs/diagrams/architecture_diagram.md)**
14. **[ER Diagram Source](docs/diagrams/er_diagram.md)**
15. **[DFD Diagrams Source](docs/diagrams/dfd_diagrams.md)**
