# VL Silks Changelog

## 2026-09-27

### Phase 18 – Final E2E Playwright QA, Category Chart Fix & Project Closure

- **E2E Playwright Smoke Suite (13 / 13 Passed)**:
  - All browser-level workflows validated against isolated `vl_silks_test_db` (port 5001); `vl_silks_db` untouched.
  - Viewports tested: Desktop, Laptop, and Mobile Chromium viewports.
  - Workflows covered: Login/Logout, Dashboard KPIs, POS checkout, invoice print, credit PDF generation, return processing, all 5 report types (Sales/Purchase/Inventory/Credit Aging/Profit), RBAC staff-restriction enforcement.
  - 0 console errors, 0 failed network requests across all 13 tests.

- **Category Sales Doughnut Chart Fix**:
  - Root cause: `.d-flex.align-items-center.justify-content-center` on `.chart-container` collapsed the Chart.js canvas to zero height.
  - Fix: Removed conflicting Flexbox centering classes from `.chart-container` in `dashboard.html`; canvas now renders at full card height.
  - Verified: Chart renders correctly with seed data categories in browser.

- **Mobile Responsive UI Fix**:
  - Added `@media (max-width: 768px)` blocks in `backend/static/css/main.css` to resolve horizontal overflow on mobile viewports.
  - Topbar and `.vl_page_container` padding properly constrained on small screens.

- **Test Suite: 390 collected: 388 passed, 2 skipped across 16 Modules**:
  - Full suite verified: 388 passed, 2 skipped (390 total collected).
  - Test database isolation guards and invariant validations confirmed.

- **Database Integrity Verified**:
  - `vl_silks_db` (demo): All 15 table counts confirmed at clean baseline before and after the full QA cycle.
  - `vl_silks_test_db`: Reset to clean baseline via `database/setup_test_db.py` after Playwright QA.
  - Final timestamped backup: `scratch/vl_silks_db_final_backup_20260927_073333.sql` (38.61 KB).

- **Documentation Updates**:
  - `README.md`: Project status updated to reflect 390 tests collected (388 passed, 2 skipped across 16 test modules) + 13/13 Playwright E2E results across Phases 0–18.
  - `PROJECT_DOCUMENTATION.md`: Full 16-module breakdown (390 tests collected: 388 passed, 2 skipped), Playwright E2E QA results, mysql-connector-python driver.
  - `docs/TESTING.md`: Summary table updated with exact 16-module test counts.
  - `docs/VIVA_QA.md`: Q23, Q27, and technology stack answers updated to mysql-connector-python and 390 tests collected + Playwright details.

## 2026-09-26

### Final Project Reconciliation & Consistency Audit

- **TODO.md & README.md Reconciliation**:
  - Reconciled historical TODO checklist items in Phase 2 and Phase 3: verified core authentication/RBAC and table styling, and explicitly documented minor non-essential UI polish items (custom SVG empty table graphics, global AJAX spinner, generic reusable delete modals) as remaining scope limitations.
  - Updated `README.md` to accurately reflect verified core completion (Phases 0–17) with 335 passing tests and links to master college documentation.
- **Normalization Claims Verification**:
  - Audited `database/schema.sql` against `docs/NORMALIZATION.md`.
  - Replaced unsupported BCNF claims with formal, defensible **3NF Normalization Analysis** and documented the business rationale for point-in-time financial snapshot preservation (`total_amount`, `balance_amount`, `running_balance`).
- **Documentation & Diagram Artifact Cleanup**:
  - Stripped all stray backtick artifacts across all `docs/*.md` files.
  - Verified zero credentials/secrets across documentation files.
  - Generated `PROJECT_DOCUMENTATION.md` at project root as a unified master college report.
  - Created verified diagram source files in `docs/diagrams/` (`architecture_diagram.md`, `er_diagram.md`, `dfd_diagrams.md`).
- **Final Test Verification**:
  - Ran full test suite via `.venv\Scripts\pytest -q`: **335 / 335 passed** (100% pass rate).

### Phase 17 Implemented – College Documentation & Viva Preparation

- **Comprehensive Documentation Suite (`docs/`)**:
  - Produced 12 authoritative, college-grade technical documents accurately matching the implemented codebase and database schema:
    1. `docs/PROJECT_ABSTRACT.md`: Formal abstract with real-world Indian retail problem domain, key modules, and keywords.
    2. `docs/PROBLEM_STATEMENT.md`: Multi-variant inventory complexity, paper Udhaar vulnerabilities, existing vs. proposed system comparative matrix, and 10 core objectives.
    3. `docs/SYSTEM_ARCHITECTURE.md`: 3-Tier architectural blueprint, Flask Application Factory pattern, dedicated Service Layer design, and Decimal precision guarantees.
    4. `docs/ER_DIAGRAM.md`: Complete 15-table Mermaid Entity-Relationship diagram, cardinality definitions, foreign key rules (`RESTRICT`, `CASCADE`, `SET NULL`), and polymorphic reference specifications.
    5. `docs/DFD.md`: Context Level (Level 0), Subsystem Decomposition (Level 1), and Transaction Detail (Level 2) Data Flow Diagrams for POS Checkout and Customer Returns/Exchanges.
    6. `docs/DATABASE_SCHEMA.md`: Full 15-table reference with column definitions, data types, constraints, default values, and index specifications.
    7. `docs/NORMALIZATION.md`: Formal proofs for 1NF, 2NF, and 3NF normalization analysis with before/after retail database normalization examples.
    8. `docs/MODULES.md`: Comprehensive breakdown of all 10 core system subsystems, routes, REST APIs, templates, and service responsibilities.
    9. `docs/SECURITY.md`: Scrypt password hashing, session security, RBAC decorator matrix (`@login_required`, `@admin_required`), 100% parameterized SQL query enforcement, and ACID transaction rollback guarantees.
    10. `docs/TESTING.md`: Detailed test suite architecture, breakdown of 335 automated test cases across 13 test modules, negative test scenarios, and data integrity verification.
    11. `docs/WORKFLOWS.md`: Step-by-step transaction algorithms for POS Checkout (`ProcessSaleCheckout`), Customer Returns (`ProcessCustomerReturn`), and Credit Settlement (`ProcessCreditSettlement`).
    12. `docs/VIVA_QA.md`: Comprehensive 60-question Viva Voce preparation guide organized into 10 technical domains covering design patterns, edge cases, financial arithmetic, and concurrency.
- **Repository Index & Roadmap Updates**:
  - Updated `README.md` with complete Project Status (All 17 Phases Completed), quick-start instructions, test execution guide, and clickable links to all 12 college documentation files.
  - Updated `TODO.md` marking all Phase 17 deliverables as completed `[x]`.

### Phase 16 Implemented – Comprehensive Testing, QA & System Verification

- **Comprehensive Test Suite Audit & Expansion**:
  - Audited all 13 existing module test suites covering Authentication, Products, Categories, Suppliers, Purchases, Inventory, Sales/POS, Customers, Credit/Udhaar, PDF generation, Returns/Exchanges, Dashboard, and Reports.
  - Added new end-to-end integration and security verification test suite `tests/test_phase16_verification.py` (10 tests) bringing total automated suite from **325 to 335 tests** with a **100% pass rate** (0 failures, 0 errors, 0 skips).
- **Core Integration & Robustness Verification**:
  - *Product CRUD & Variant Life-Cycle*: Verified complete product and multi-variant creation, duplicate SKU/barcode enforcement, status deactivations, and metadata edit decoupling (zero silent inventory corruption).
  - *Purchase & Stock Integrations*: Verified atomic stock increments with `PURCHASE` stock movement audit trail, supplier checks, and full multi-item rollback safety without leaving orphaned or partial records.
  - *Sales & Udhaar Credit Reconciliation*: Verified cash, UPI, card, and credit sales, split payments, stock deductions, `SALE` movement auditing, overpayment prevention, and mathematical reconciliation between `credit_transactions` and `credit_service.calculate_customer_outstanding_balance()`.
  - *Returns & Exchanges*: Verified `RESTOCKABLE` vs `DAMAGED` stock handling, `CASH` vs `CREDIT_ADJUSTMENT` refunds, multi-item garment exchanges, price difference accounting, and over-return rejections.
  - *Negative Stock Prevention*: Verified that sales, manual stock adjustments, purchase rollbacks, and exchange operations strictly enforce non-negative stock invariants.
  - *RBAC & Security Matrix*: Verified role-based enforcement across all endpoints (Anonymous redirects/401, Staff operational access, Admin-only controls for sensitive mutations).
  - *PDF Generation*: Verified PDF magic bytes (`%PDF-1.4`), customer header metadata, multi-page layout, and financial consistency against `credit_service`.
  - *Dashboard & Business Reports Consistency*: Verified that real-time dashboard KPIs, sales reports, inventory valuations, and credit aging schedules derive from the exact same underlying transactional truth.
- **Defects Discovered and Fixed**:
  - `backend/services/report_service.py`: Fixed `KeyError: 'city'` in `get_credit_aging_report` by incorporating `COALESCE(c.address, '') AS address` in the SQL query and providing backward-compatible city mapping; fixed purchase report paid/due metric summaries and CSV headers.
  - `backend/templates/reports/credit_aging.html`: Fixed template link routing from non-existent `credit.customer_ledger` to canonical `credit.view`.
- **Responsive UI Verification**:
  - Conducted static CSS and template audit across all 13 core views across 5 standard viewport widths: 360px, 390px, 768px, 1024px, and 1366px.
  - Verified responsive offcanvas sidebar navigation with toggle button, `.table-responsive` overflow containers on all data tables, flex-wrapping grid layouts, touch-friendly action buttons, and responsive modal/form controls.
- **Final Test Count**: **335 passed** in 119.20s. Phase 17 college documentation and viva preparation preserved untouched for subsequent execution.

### Phase 15 Implemented – Business Reports & Analytics Export

- Created `backend/services/report_service.py` — authoritative Business Reporting service with exact Decimal calculations:
  - `get_sales_report(start_date, end_date)`: Generates comprehensive sales analytics with invoice count, total revenue, discount totals, paid amounts, Udhaar credit amounts, payment method breakdowns, and line-item unit aggregations.
  - `export_sales_report_csv(start_date, end_date)`: Generates CSV export for sales records with complete summaries.
  - `get_purchase_report(start_date, end_date)`: Aggregates inward purchase bills, supplier totals, unit counts, paid/due amounts, and supplier-wise breakdown.
  - `export_purchase_report_csv(start_date, end_date)`: Generates CSV export for purchase logs with supplier summaries.
  - `get_inventory_valuation_report()`: Computes total inventory valuation at cost price vs selling price, potential gross margins, variant counts, and low-stock indicators across all active garment categories.
  - `export_inventory_valuation_csv()`: Generates CSV export of inventory stock and valuation metrics.
  - `get_credit_aging_report()`: Generates chronological Udhaar aging analysis with aging buckets (0–30 Days, 31–60 Days, 61–90 Days, 90+ Days) for all credit customers.
  - `export_credit_aging_csv()`: Generates CSV export of Udhaar credit aging schedules.
  - `get_profit_report(start_date, end_date)`: Computes itemized and categorical gross profit margins (Selling Price − Purchase Cost) with units sold, revenue, total cost, and profit percentage.
  - `export_profit_report_csv(start_date, end_date)`: Generates CSV export of profit analysis.
- Created `backend/routes/reports.py` — Reports Blueprint with Web views and REST/CSV API endpoints:
  - `GET  /reports` — Central Reports Navigation Hub
  - `GET  /reports/sales`, `GET  /api/reports/sales`, `GET  /api/reports/sales/csv`
  - `GET  /reports/purchases`, `GET  /api/reports/purchases`, `GET  /api/reports/purchases/csv`
  - `GET  /reports/inventory-valuation`, `GET  /api/reports/inventory-valuation`, `GET  /api/reports/inventory-valuation/csv`
  - `GET  /reports/credit-aging`, `GET  /api/reports/credit-aging`, `GET  /api/reports/credit-aging/csv`
  - `GET  /reports/profit`, `GET  /api/reports/profit`, `GET  /api/reports/profit/csv`
- Created Jinja templates in `backend/templates/reports/`:
  - `index.html` — Card-based report navigator with quick summaries
  - `sales.html` — Sales report with date range filters, KPI widgets, and payment breakdown table
  - `purchases.html` — Inward purchase report with date filters and supplier summary
  - `inventory_valuation.html` — Stock valuation with category summaries and cost vs selling charts
  - `credit_aging.html` — Udhaar aging breakdown by 30-day buckets with direct links to customer credit profiles
  - `profit.html` — Gross profit margin report with profitability rankings and date filters
- Created comprehensive test suite `tests/test_reports.py` (38 tests) covering all 5 reports, auth protection, REST APIs, CSV downloads, and service methods.
- Verified all 325/325 automated tests pass cleanly across all system modules.

### Phase 14 Implemented – Dashboard Polish & Analytics

- Created `backend/services/dashboard_service.py` — dedicated business service for real-time shop statistics and analytics:
  - `get_dashboard_summary()`: Aggregates catalog stats (products, categories, variants, total stock, low stock count), sales stats (today sales/count, month sales/count, all-time totals), returns stats (today/month refund amounts and counts, net sales calculation), and credit totals from `credit_service`.
  - `get_recent_sales(limit)`: Retrieves latest completed customer invoices with customer names, phone numbers, payment statuses, and amounts.
  - `get_low_stock_items(limit)`: Identifies active variants whose stock quantity is at or below minimum threshold.
  - `get_monthly_sales(months)`: Computes month-by-month sales revenue, cash/paid collections, credit amounts, and invoice counts for trend analysis.
  - `get_top_products(limit)`: Ranks top selling garments based on units sold and total revenue.
  - `get_category_distribution()`: Aggregates category-wise revenue and unit sales for distribution charts.
- Updated `backend/routes/dashboard.py` with full REST API and view support:
  - `GET  /dashboard` — Main shop performance overview with Chart.js charts, top products, recent sales, low stock alerts, and customer credit ledger summary
  - `GET  /api/dashboard/summary` — Real-time KPI metrics payload
  - `GET  /api/dashboard/recent-sales` — Latest invoices list endpoint
  - `GET  /api/dashboard/low-stock` — Low stock inventory alerts endpoint
  - `GET  /api/dashboard/monthly-sales` — 6-month & 12-month trend charting data endpoint
  - `GET  /api/dashboard/top-products` — Top selling products endpoint
  - `GET  /api/dashboard/category-distribution` — Category revenue distribution endpoint
- Enhanced `backend/templates/dashboard.html`:
  - Integrated interactive Chart.js charts: Monthly Sales Trend (dual-axis bar/line chart) and Category Sales Breakdown (donut chart).
  - Added real-time AJAX stats refresh button with spinner animation and live timestamp badge.
  - Added dedicated Top Selling Garments card with ranked medals (#1, #2, #3).
  - Added direct quick links to POS billing (`/sales/new`), Purchase inward (`/purchases/new`), Customer Credit ledger (`/credit`), and Inventory (`/inventory`).
  - Corrected all invoice and statement direct view links.
- Created `tests/test_dashboard.py` (12 tests) verifying:
  - Anonymous vs authenticated redirect behavior for `/` and `/dashboard`
  - Web dashboard HTML rendering with charts and cards
  - All 6 REST API endpoints (`/summary`, `/recent-sales`, `/low-stock`, `/monthly-sales`, `/top-products`, `/category-distribution`)
  - Dashboard service unit calculations (net sales, 12-month interval processing)
- Updated `TODO.md` and `API_SPEC.md`.

### Phase 13 Implemented – Returns & Exchanges

- Created `backend/services/return_service.py` — authoritative Returns & Exchanges service:
  - `get_all_returns(search, refund_type, date_from, date_to)`: List all returns with customer and invoice details, item counts, and totals. Supports full-text search and date-range filtering.
  - `get_return_summary_metrics()`: Returns dashboard KPIs — total/today return counts, total/today refund amounts, exchanges count, credit adjustments count.
  - `get_return_by_id(return_id)`: Fetch complete return record with all return items, product info, and condition breakdown.
  - `get_sale_returnable_items(sale_id)`: Calculates remaining returnable quantity per line item, accounting for all prior returns on that sale (partial-return-safe).
  - `create_return(return_data, items_data, user_id)`: Atomic transaction processing customer garment returns:
    - Row-level `FOR UPDATE` locking on `sales`, `sale_items`, and `product_variants`
    - Server-side refund amount calculation from original net selling price (cannot be manipulated by client)
    - `RESTOCKABLE`: increments `product_variants.stock_quantity` + creates `CUSTOMER_RETURN` stock movement
    - `DAMAGED`: audit-only `DAMAGE` movement created, stock is NOT restored
    - `CREDIT_ADJUSTMENT`: inserts `credit_transactions` record (`RETURN_REFUND`) to reduce Udhaar balance
    - `CASH`: no ledger entry (physical cash returned at counter)
    - All-or-nothing rollback on any failure
    - Historical sale records remain immutable (never edited/deleted)
  - `process_exchange(exchange_data, old_items_data, new_items_data, user_id)`: Atomic garment exchange:
    - Validates old item returnable quantities and new variant availability and ACTIVE status
    - Restocks old variants (if RESTOCKABLE) with `CUSTOMER_RETURN` movement
    - Deducts new replacement variant stock with `SALE` movement under reference `RETURN`
    - Calculates price_difference = new_value − old_value and reports payment_status
    - Optional `CREDIT_ADJUSTMENT` for negative difference via `credit_transactions`
    - Full atomicity and rollback protection
- Created `backend/routes/returns.py` — Returns Blueprint with Web + REST API endpoints:
  - `GET  /returns` — Returns & Exchanges directory with summary metrics, search, and date filtering
  - `GET  /returns/new[?sale_id=&mode=]` — Return/Exchange form, pre-loaded with invoice if sale_id provided
  - `POST /returns/new` — Process RETURN or EXCHANGE form submission
  - `GET  /returns/<return_id>` — Detailed return view with items, conditions, and audit trail
  - `GET  /api/returns` — REST: list returns with filtering
  - `GET  /api/returns/<return_id>` — REST: return record detail
  - `GET  /api/returns/sale/<sale_id>/returnable-items` — REST: calculate returnable quantities
  - `POST /api/returns` — REST: create atomic return
  - `POST /api/returns/exchange` — REST: process atomic exchange
- Created web templates:
  - `backend/templates/returns/index.html` — Returns list with dashboard summary cards
  - `backend/templates/returns/new.html` — Dynamic return/exchange form with invoice lookup
  - `backend/templates/returns/view.html` — Return detail view with condition breakdown and audit
- Registered `returns_bp` in `backend/app.py`.
- Updated `backend/templates/base.html` to activate Returns sidebar link.
- Updated `backend/templates/sales/view.html` to add Return/Exchange action button.
- Added comprehensive test suite in `tests/test_returns.py` (37 tests) covering:
  - Service listing, metrics, and returnable item calculation
  - Cash and credit refund returns with stock movement verification
  - RESTOCKABLE vs DAMAGED condition handling (stock/no-stock)
  - Server-side refund calculation enforcement
  - Over-return prevention and duplicate return rejection
  - Partial return followed by remaining-quantity return
  - Historical sale immutability after return
  - Exchange workflow: stock restock and deduction, price difference computation
  - Exchange of already-returned items is rejected
  - DAMAGED old item in exchange does not restore stock
  - REST API: 200/201/400/404 coverage
  - Web route: auth gate, staff/admin access, redirect-on-not-found
- Updated `TODO.md` and `API_SPEC.md`.

### Phase 12 Implemented – Credit / Udhaar PDF Statement


- Implemented authoritative PDF Statement Generator in `backend/services/pdf_service.py` using ReportLab:
  - `generate_credit_statement_pdf(customer_id, date_from=None, date_to=None)`: Generates official A4 portrait statement PDF with complete customer info, statement period, financial KPI summary cards, chronological transaction table with repeating headers, and settlement terms.
  - Implemented `NumberedCanvas` two-pass page renderer to dynamically calculate total page count and draw running headers, gold accent lines, timestamps, and page numbers ("Page X of Y") across multi-page ledgers.
  - Built-in VL Silks brand styling using primary maroon (`#8B0000`), royal gold (`#D4AF37`), warm cream (`#FFF8E1`), and deep charcoal (`#333333`) color scheme.
  - High-resolution logo rendering with graceful textual branding fallback if image assets are inaccessible.
  - Reuses authoritative `credit_service.get_customer_credit_profile` and `credit_service.get_customer_credit_history` to ensure 100% financial consistency with the REST API.
  - Strict read-only invariant: PDF generation does not mutate any sales, payments, credit transactions, customer records, or stock.
  - Robust date filtering: validates `date_from` and `date_to` (format YYYY-MM-DD, `date_from <= date_to`), computing accurate period charges and settlements while preserving authoritative lifetime outstanding balances.
  - Sanitized meaningful filename generation (e.g. `VL-Silks-Credit-Statement-Ramesh_Kumar-ID1.pdf` and period-specific filenames).
- Implemented PDF Blueprint in `backend/routes/pdf.py`:
  - `GET /api/pdf/credit/<customer_id>`: REST endpoint streaming `application/pdf` with `Content-Disposition: attachment`. Enforces authentication (401), customer existence (404), date validation (400), and handles unexpected errors (500).
  - `GET /credit/customer/<customer_id>/statement`: Direct Web download route for browsers, integrated with Flask session auth and flash messages.
- Registered `pdf_bp` in `backend/app.py`.
- Updated Web Templates:
  - `backend/templates/credit/view.html`: Added "Download Credit Statement" action button and interactive Bootstrap modal `#statementModal` for custom statement period selection or full history download.
  - `backend/templates/customers/view.html`: Added direct "Download Credit Statement (PDF)" link.
- Added comprehensive test suite in `tests/test_pdf.py` (21 tests) covering authentication, PDF magic bytes, headers, 404/400 validations, period filtering, multi-page ledger pagination, empty history, inactive customers, logo fallback, read-only idempotency, and web routes.
- Updated `API_SPEC.md` and `TODO.md`.

## 2026-09-25

### Phase 11 Implemented – Credit / Udhaar Management

- Created authoritative Credit Service in `backend/services/credit_service.py`:
  - `get_credit_summary()`: Aggregates system-wide Udhaar totals — total outstanding, total customers with balance, highest individual debtor, and average balance.
  - `calculate_total_credit_outstanding()` / `calculate_customer_outstanding_balance(customer_id)`: Compute exact Decimal balances directly from `credit_transactions` (CREDIT_SALE debits − PAYMENT + RETURN_REFUND credits) as the single authoritative source of truth.
  - `get_credit_customers(search, status, min_balance)`: Directory of customers with an outstanding Udhaar balance, filterable by name/phone search, customer status, and minimum balance threshold.
  - `get_customer_credit_profile(customer_id)`: Full financial profile including credit limit, outstanding balance, available credit, and ledger aggregate stats.
  - `get_customer_credit_history(customer_id)`: Chronological ledger of all `credit_transactions` with computed per-entry `debit_amount`, `credit_amount`, and `running_balance` columns.
  - `record_credit_payment(customer_id, payment_data, user_id)`: Atomic settlement using row-level `FOR UPDATE` lock to prevent race conditions. Records both a `payments` row and a `credit_transactions` row (`transaction_type = 'PAYMENT'`) in a single transaction. Prevents overpayment; validates amount, payment method, customer existence, and date.
  - `validate_settlement_data()`: Comprehensive input validation with Decimal arithmetic throughout.
  - All financial arithmetic uses Python `Decimal` with `.quantize(Decimal('0.01'))` — zero float arithmetic.
- Created Web routes in `backend/routes/credit.py` and templates in `backend/templates/credit/`:
  - `GET /credit`: Credit directory with 4 metric summary cards (Total Outstanding, Customers with Udhaar, Highest Debtor, Average Balance), search, status filter, and sortable table.
  - `GET /credit/customer/<id>`: Customer credit profile with outstanding/available balances, credit limit bar, and full chronological ledger table with debit/credit columns and running balance.
  - `GET /credit/customer/<id>/payment` & `POST /credit/customer/<id>/payment`: Settlement payment form with max-amount enforcement from current outstanding balance.
- REST API endpoints registered:
  - `GET /api/credit/summary` — System-wide Udhaar summary.
  - `GET /api/credit/customers` — Credit customer directory (search, status, min_balance filters).
  - `GET /api/credit/customer/<id>` — Customer credit profile (404 if not found).
  - `GET /api/credit/customer/<id>/history` — Chronological ledger with `count`, `ledger` keys.
  - `POST /api/credit/customer/<id>/payment` — Atomic settlement payment (login required, returns 201 on success, 400 on validation error, 401 on unauthenticated).
- Dashboard integration: `backend/routes/dashboard.py` refactored to use `credit_service.get_credit_summary()` and `credit_service.get_credit_customers()` as the single source of truth — `Total Credit to Collect` on dashboard and `/api/dashboard/summary` now always agree exactly with `/api/credit/summary`.
- Sidebar updated in `backend/templates/base.html`: Credit / Udhaar Ledger link added.
- Customer view updated in `backend/templates/customers/view.html`: "View Credit Ledger" button added.
- Fixed `backend/templates/dashboard.html`: credit table column was referencing non-existent `cust.total_outstanding` — corrected to `cust.outstanding_balance` (the actual field returned by `credit_service.get_credit_customers()`).
- Fixed `backend/services/credit_service.py`:
  - Credit transaction notes now include reference number in audit trail when provided.
  - `profile['credit_limit']` is now stored as `Decimal` type for consistent invariant comparisons.
- Created 36 automated test cases in `tests/test_credit.py` covering:
  - Credit summary accuracy (database-derived vs service aggregate).
  - Credit customer directory with search, status, and min_balance filtering.
  - Customer credit profile and financial invariant (outstanding + available = credit_limit).
  - Chronological ledger ordering and deterministic running balance.
  - Settlement payment: success, zero/negative rejection, overpayment rejection, invalid customer/method/amount rejection, notes & reference number persistence.
  - Web routes: unauthenticated redirect, staff and admin access.
  - REST API: all 5 endpoints including auth guard.
  - Integration: full POS credit sale → credit service balance → settlement → balance reduction cycle.
  - Dashboard credit total vs credit summary agreement.
  - Same-date transaction deterministic ordering.
- Fixed `tests/test_sales.py::test_create_credit_sale_success`: Test now creates a dedicated customer with `credit_limit = 100,000` to avoid seed-data credit exhaustion failure. Cleanup uses correct `reference_id` column (not `sale_id`) on `stock_movements` table.
- Updated `TODO.md`: All 6 Phase 11 items marked `[x]`.
- **Test status: 217 tests collected — 100% pass rate.**

---



### Phase 10 Implemented – Customer Management

- Implemented Customer Service in `backend/services/customer_service.py`:
  - Customer directory retrieval with SQL subquery aggregation on `sales` to compute accurate lifetime metrics (`total_purchases`, `total_purchase_value`, `total_paid`, `outstanding_balance`) without double-counting across multi-item sales or split payments.
  - Multi-criteria search across customer name, unique phone number, and email.
  - Phone uniqueness validation on both create and update (permitting the customer's own phone during updates while rejecting collisions).
  - Customer profile and purchase history retrieval (`get_customer_purchase_history()`) with line item and quantity counts.
  - Summary metrics computation: Total Customers, Active Customers, Customers with Outstanding Udhaar Balance, and Total Outstanding Credit Receivables.
  - Safe customer deactivation (`delete_customer()`, `toggle_customer_status()`) setting `status = 'INACTIVE'` while strictly preserving historical sales, sale items, payments, and credit transactions.
  - Reused POS customer search and quick-registration logic seamlessly between `customer_service` and `sale_service` without breaking Phase 9 POS workflows.
- Created Web routes in `backend/routes/customers.py` and templates in `backend/templates/customers/`:
  - `GET /customers`: Customer directory table with 4 metric summary cards, search (name/phone/email), and status filtering.
  - `GET /customers/new` & `POST /customers/new`: Customer registration form with validation and credit limit configuration (Admin only).
  - `GET /customers/<id>`: Customer profile view with lifetime purchase stats, available credit limit calculator, and recent invoices table.
  - `GET /customers/<id>/edit` & `POST /customers/<id>/edit`: Customer edit form with validation (Admin only).
  - `GET /customers/<id>/purchases`: Dedicated invoice history page with links to sales vouchers.
  - `POST /customers/<id>/toggle-status`: Safe status toggling without data destruction (Admin only).
- Implemented REST API endpoints:
  - `GET /api/customers`: Customers list with search, phone, and status filtering.
  - `GET /api/customers/:id`: Customer detail with financial statistics and full purchase history.
  - `POST /api/customers`: Customer creation endpoint with validation (Admin only).
  - `PUT /api/customers/:id`: Customer update endpoint (Admin only).
  - `DELETE /api/customers/:id`: Safe deactivation endpoint (Admin only).
- Connected Customers sidebar navigation link in `backend/templates/base.html` to `url_for('customers.index')`.
- Added 37 automated test cases in `tests/test_customers.py` covering all CRUD, search, validation, deactivation, role access, and POS preservation scenarios (181 total project tests passing — **100% pass rate**).
- Updated `TODO.md`, `API_SPEC.md`, and `CHANGELOG.md`.

---

### Phase 9 Implemented – Sales & Billing (POS)

- Implemented Sale Service in `backend/services/sale_service.py`:
  - Atomic transaction: saves `sales`, `sale_items`, decrements `product_variants.stock_quantity`, records `stock_movements` (`movement_type = 'SALE'`, `reference_type = 'SALE'`), and records `payments` (for non-credit) or `credit_transactions` (`CREDIT_SALE`) and customer balance updates for credit.
  - Validation engine: active customer check, active product/variant enforcement, duplicate variant rejection within one sale, positive quantity, non-negative prices, sufficient stock pre-check with authoritative row-level lock in transaction.
  - Authoritative `Decimal` financial calculations: `line_total = qty * unit_price - item_discount`, `subtotal = SUM(line_total)`, `total_amount = subtotal - discount + tax`, `balance_amount = total_amount - paid_amount`.
  - Auto-generated invoice numbers in `SALE-YYYY-NNNN` format.
  - Metrics: total sales count/revenue/outstanding, month-to-date count/revenue, credit sales count.
  - Added `get_active_variants_for_sale(search=)` with optional search across name, SKU, brand, barcode.
  - Added `get_active_customers(search=)` with live balance aggregation (`current_balance`, `available_credit`).
  - Added `quick_create_customer()` for POS in-flow customer registration with phone uniqueness validation.
- Created Web routes in `backend/routes/sales.py` and templates in `backend/templates/sales/`:
  - `GET /sales`: Invoice list with 6 summary metric cards, search (invoice/customer), payment method, payment status, and date range filters.
  - `GET /sales/new` & `POST /sales/new`: Full POS interface with live variant search, cart management, subtotal/discount/tax/total preview, all payment methods, and customer lookup.
  - `GET /sales/<id>`: Print-ready invoice view with line items, customer details, and full totals.
- Implemented REST API endpoints:
  - `GET /api/sales`: Sales listing with filtering.
  - `GET /api/sales/<id>`: Single sale with full line items (returned at both `sale.items` and top-level `items` key).
  - `POST /api/sales`: Atomic sale creation endpoint (authenticated).
  - `GET /api/pos/variants/search?q=`: Live variant search for POS.
  - `GET /api/pos/customers/search?q=`: Live customer search with balance data for POS.
  - `POST /api/pos/customers/quick-create`: Quick customer registration from POS checkout modal.
- Fixed stale test assertions in `test_phase1.py` and `test_products.py` to be database-driven (not brittle hardcoded values from seed data that drift as tests create new records).
- Added 14 automated test cases in `tests/test_sales.py` (144 total project tests passing — **100% pass rate**).
- Updated `TODO.md` and `CHANGELOG.md`.

---

### Phase 8 Implemented – Inventory Management

- Implemented Inventory Service in `backend/services/inventory_service.py`:
  - Current stock management derived authoritatively from `product_variants.stock_quantity`.
  - Computed stock health statuses: `IN_STOCK` (stock > min_stock), `LOW_STOCK` (0 < stock <= min_stock), and `OUT_OF_STOCK` (stock = 0).
  - Search across product name, brand, SKU, barcode, color, size, and category with SQL-level parameterization.
  - Low stock query (`get_low_stock_items()`) computing units needed for replenishment.
  - Out of stock query (`get_out_of_stock_items()`) tracking critical shelf stockouts.
  - Stock movement audit trail (`get_stock_movements()`) with joins across variants, products, categories, and recording users.
  - Atomic manual stock adjustments (`adjust_stock()`) for `INCREASE` and `DECREASE` with row-level locks, negative stock prevention, and audit movements (`movement_type = 'ADJUSTMENT'`).
  - Atomic damaged stock write-offs (`record_damaged_stock()`) with audit movements (`movement_type = 'DAMAGE'`).
- Created Web routes in `backend/routes/inventory.py` and templates in `backend/templates/inventory/`:
  - `GET /inventory`: Main stock directory with 4 summary metric cards, search, category filter, and stock level filter tabs.
  - `GET /inventory/low-stock`: Dedicated low stock monitor with replenishment advisory.
  - `GET /inventory/out-of-stock`: Critical stockout monitor.
  - `GET /inventory/movements`: Chronological stock movement audit ledger with multi-criteria filtering (movement type, reference type, date range, search).
  - `GET /inventory/adjustment` & `POST /inventory/adjustment`: Admin stock adjustment and damage write-off form with dynamic calculation preview.
- Implemented REST API endpoints:
  - `GET /api/inventory`: JSON inventory list with computed stock status and query filters.
  - `GET /api/inventory/low-stock`: JSON list of low stock items.
  - `GET /api/inventory/movements`: JSON list of stock movement logs.
  - `POST /api/inventory/adjustment`: Atomic stock adjustment / damaged write-off API (Admin only).
- Connected Inventory & Stock sidebar nav item to `/inventory`.
- Added 40 automated test cases in `tests/test_inventory.py` (130 total project tests passing with 100% success rate).
- Updated `TODO.md`, `CHANGELOG.md`, and `API_SPEC.md`.

---

### Phase 7 Implemented – Purchases / Inward Stock

- Implemented Purchase Service in `backend/services/purchase_service.py`:
  - Atomic transaction handling: saves `purchases`, `purchase_items`, updates `product_variants.stock_quantity`, and records `stock_movements` (movement_type: `PURCHASE`, reference_type: `PURCHASE`).
  - Validation engine: active supplier enforcement, active product/variant verification, duplicate variant rejection within the same purchase, positive quantities (`> 0`), non-negative prices (`>= 0`), and non-negative grand totals.
  - Authoritative financial calculations using `Decimal` arithmetic: `line_total = quantity * unit_price`, `subtotal = SUM(line_total)`, `grand_total = subtotal - discount + tax`.
  - Metrics computation: Total Purchases, Total Purchase Value, Current Month count/value, and Pending/Unpaid payable amounts.
- Created Web routes in `backend/routes/purchases.py` and templates in `backend/templates/purchases/`:
  - `GET /purchases`: Inward purchases directory with summary metric cards, search (invoice & supplier), supplier dropdown filter, status filter, and date filters.
  - `GET /purchases/new` & `POST /purchases/new`: Dynamic inward stock creation form with interactive variant selector, real-time line total / grand total client preview, duplicate variant prevention, and authoritative server recalculation.
  - `GET /purchases/<id>`: Printable inward voucher and bill view with supplier details, consignment items breakdown, financial summary, and viva-ready inventory impact / stock movement audit cards.
- Implemented REST API endpoints:
  - `GET /api/purchases`: Purchases listing with filtering.
  - `GET /api/purchases/:id`: Single purchase with full line item details.
  - `POST /api/purchases`: Atomic purchase and stock increment creation endpoint (Admin only).
- Connected Purchases sidebar nav item to `/purchases`.
- Added 33 automated test cases in `tests/test_purchases.py` (90 total project tests passing with 100% success rate).
- Updated `TODO.md`, `CHANGELOG.md`, and `API_SPEC.md`.

---

### Phase 6 Implemented – Supplier Management

- Implemented Supplier Service in `backend/services/supplier_service.py`:
  - Full CRUD with field validation: `supplier_name` and `phone` required; email validated for basic format.
  - Purchase count and total purchase value aggregated via LEFT JOIN to `purchases`.
  - Supplier purchase history via `get_supplier_purchase_history()` with item count.
  - Safe status toggle (`ACTIVE` / `INACTIVE`) preserving all purchase records.
- Created Web routes in `backend/routes/suppliers.py` and templates in `backend/templates/suppliers/`:
  - `GET /suppliers`: Supplier directory with search (name/contact/phone/email), status filter, 3 metric cards.
  - `GET /suppliers/new` & `POST /suppliers/new`: Create form with business info, contact, GST, and status.
  - `GET /suppliers/<id>`: Supplier profile with stats, business detail panel, and purchase history table.
  - `GET /suppliers/<id>/edit` & `POST /suppliers/<id>/edit`: Edit form with purchase count advisory banner.
  - `POST /suppliers/<id>/toggle-status`: Safe status toggle.
- Implemented REST API endpoints:
  - `GET /api/suppliers`, `GET /api/suppliers/:id`, `POST /api/suppliers`, `PUT /api/suppliers/:id`, `DELETE /api/suppliers/:id` (safe deactivation).
  - `GET /api/suppliers/:id/purchases` — purchase history for a specific supplier.
- Connected Suppliers sidebar nav item to `/suppliers`.
- Added 22 automated test cases in `tests/test_suppliers.py` (57 total project tests passing).
- Updated `TODO.md` and `CHANGELOG.md`.

---


### Phase 5 Implemented – Category Management

- Implemented Category Service in `backend/services/category_service.py`:
  - Category retrieval with live aggregated product counts (`product_count`) and cumulative stock volumes.
  - Case-insensitive & trimmed duplicate name validation.
  - Safe category deactivation (`status = 'INACTIVE'`) preserving product relationships and historical integrity.
- Created Web routes and templates in `backend/routes/categories.py` and `backend/templates/categories/`:
  - `GET /categories`: Directory table with search, status filtering, product count links, stock volume, and admin controls.
  - `GET /categories/new` & `POST /categories/new`: Create category form with duplicate prevention.
  - `GET /categories/<id>/edit` & `POST /categories/<id>/edit`: Edit category specifications with product dependency information.
  - `POST /categories/<id>/toggle-status`: Safe status toggling without impacting catalog garments.
- Implemented REST API endpoints in `backend/routes/categories.py`:
  - `GET /api/categories`, `GET /api/categories/:id`, `POST /api/categories`, `PUT /api/categories/:id`, `DELETE /api/categories/:id` (safe deactivation).
- Connected sidebar navigation item to `/categories`.
- Added 11 automated test cases in `tests/test_categories.py` (35 total project tests passing).
- Updated `TODO.md` and `CHANGELOG.md`.

---

### Phase 4 Implemented – Products & Product Variants Management

- Implemented full Garment and Product Variant service layer in `backend/services/product_service.py`:
  - Atomic product and variant creation (`create_product_with_variants`).
  - Validation engine: required fields, unique SKUs (per-submission and database-wide), unique barcodes, category checks, non-negative purchase/selling prices and minimum stock thresholds.
  - Variant stock status computation: `IN_STOCK` (stock > min_stock), `LOW_STOCK` (0 < stock <= min_stock), and `OUT_OF_STOCK` (stock = 0).
  - Stock safety: strictly decoupled metadata updates from inventory quantities to maintain stock movement integrity.
- Created Web routes and templates in `backend/routes/products.py` and `backend/templates/products/`:
  - `GET /products`: Products catalog with live search across name/brand/SKU/barcode, dynamic category filter, status filter, and summary metrics.
  - `GET /products/new` & `POST /products/new`: Interactive garment builder with dynamic variant rows (+ Add Variant / Remove Variant) and client/server validation.
  - `GET /products/<id>`: Detailed garment specifications, stock health overview cards, and complete variant breakdown table with status badges.
  - `GET /products/<id>/edit` & `POST /products/<id>/edit`: Base garment editing, existing variant price/min-stock/status updating, and variant additions.
  - `POST /products/<id>/toggle-status` & `POST /products/variants/<id>/toggle-status`: Safe deactivation toggles.
- Implemented complete REST API endpoints in `backend/routes/products.py`:
  - `GET /api/products`, `GET /api/products/:id`, `POST /api/products`, `PUT /api/products/:id`, `DELETE /api/products/:id`.
  - `GET /api/products/:id/variants`, `POST /api/products/:id/variants`, `PUT /api/products/variants/:variant_id`, `DELETE /api/products/variants/:variant_id`.
- Role-based authorization enforcement: Admin full CRUD, Staff read-only view.
- Added 17 automated tests in `tests/test_products.py` verifying all 20 required scenarios (24 total project tests passing).
- Updated `API_SPEC.md` and `TODO.md`.

---

### Phase 1 Implemented – Database Schema, Backend Foundation & UI Shell

- Created full 15-table MySQL schema in `database/schema.sql`:
  - `users`, `categories`, `products`, `product_variants`, `suppliers`, `purchases`, `purchase_items`, `customers`, `sales`, `sale_items`, `payments`, `credit_transactions`, `stock_movements`, `returns`, `return_items`.
  - Added garment product variant support (`product_variants`) with unique SKU, sizes, colors, and independent stock levels (`stock_quantity >= 0`).
  - Added customer credit transaction ledger (`credit_transactions`) and inventory movement audit logs (`stock_movements`).
- Created realistic development seed data in `database/seed.sql` with hashed passwords (Werkzeug scrypt), sarees, silk dhotis, shirts, kurtis, suppliers, customers, sales, and credit transactions.
- Created Flask backend foundation in `backend/`:
  - `backend/app.py` with application factory `create_app()`, custom Jinja filters, context processors, and error handlers.
  - `backend/config.py` loading `.env` variables with fallback configurations.
  - `backend/utils/database.py` with safe connection handling, context managers, and parameterized query utilities.
  - `backend/routes/health.py` with `GET /api/health` endpoint.
  - `backend/routes/auth.py` with session-based login, logout, and role access decorators.
  - `backend/routes/dashboard.py` computing real-time business metrics including `Total Credit to Collect`.
- Created UI foundation matching VL Silks brand identity:
  - Brand color palette: Maroon `#8B0000`, Gold `#D4AF37`, Warm Cream `#FFF8E1`, Charcoal `#333333`.
  - `backend/templates/base.html`, `backend/templates/login.html`, and `backend/templates/dashboard.html`.
  - Custom brand CSS stylesheet in `backend/static/css/main.css` and `frontend/css/main.css`.
  - Static asset pipeline for official logo, monogram, and icons.
- Created automated test suite in `tests/test_phase1.py` covering startup, health endpoint, DB connectivity, 15 tables, seed data integrity, and login authentication.
- Updated `DATABASE_DESIGN.md`, `API_SPEC.md`, and `TODO.md`.

---

### Project Initialized

- Project name finalized as VL Silks
- Project title finalized
- Core modules defined
- Inventory management defined
- Credit/Udhaar management defined
- Customer credit history defined
- Credit PDF export defined
- Dashboard credit-to-collect metric defined
- Technology stack selected
- Initial database architecture defined
- Branding direction approved
- VL Silks tagline finalized: "TRADITION MEETS FASHION"