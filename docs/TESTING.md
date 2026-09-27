# Testing & Quality Assurance

## VL Silks - Comprehensive Test Suite & Verification Documentation

---

## 1. Test Suite Overview

The VL Silks system includes a comprehensive, automated test suite consisting of **390 tests collected (388 passed, 2 skipped)** across **16 test modules** using `pytest`.

### Test Summary:
- **Total Test Files / Modules:** 16
- **Total Test Cases Collected:** 390
- **Execution Results:** 388 passed, 2 skipped (0 failures, 0 errors)
- **Status:** Verified and Passing

---

## 2. Test Module Breakdown (16 Test Files)

| Module / Test File | Tests | Description / Target Scope |
|---|---|---|
| `tests/test_phase1.py` | 7 | Startup, `/api/health`, DB connectivity, 15 tables, seed data integrity (5 passed, 2 skipped) |
| `tests/test_categories.py` | 11 | Category CRUD, uniqueness validation, status toggling |
| `tests/test_products.py` | 23 | Product CRUD, multi-variant creation, SKU uniqueness, search, stock safety |
| `tests/test_suppliers.py` | 22 | Supplier master CRUD, phone/GST validation, purchase history, status filters |
| `tests/test_purchases.py` | 33 | Inward purchase invoice entry, stock increment, movement audit |
| `tests/test_inventory.py` | 40 | Real-time stock levels, movement history, manual adjustments, alerts |
| `tests/test_sales.py` | 19 | POS checkout, line discounts, payment methods, stock deduction |
| `tests/test_customers.py` | 37 | Customer profile CRUD, phone search, credit limits, purchase history |
| `tests/test_credit.py` | 36 | Udhaar ledger, balance calculation, settlement payments, overpayment rejection |
| `tests/test_pdf.py` | 21 | ReportLab PDF credit statement generation, layout, multi-page pagination |
| `tests/test_returns.py` | 63 | Returns, exchanges, restockable vs damaged items, invoice search widget |
| `tests/test_dashboard.py` | 12 | KPI computations, monthly trend aggregations, top product rankings |
| `tests/test_reports.py` | 38 | Sales, Purchase, Inventory Valuation, Credit Aging, Profit reports, CSV exports |
| `tests/test_users.py` | 13 | User management master CRUD, password updates, RBAC enforcement |
| `tests/test_database_isolation.py` | 5 | Database isolation enforcement and TestingConfig guards |
| `tests/test_phase16_verification.py` | 10 | End-to-end integration cycles and data invariant validation |
| **Total** | **390** | **Complete Full-System Coverage (388 Passed, 2 Skipped; 390 Total Collected)** |

---

## 4. Test Database Isolation Architecture

To ensure 100% data integrity and eliminate contamination of the live/demo database:

1. **Strict Configuration Enforcement (`TestingConfig`):**
   - Testing requires an explicit `TEST_DB_NAME` environment variable (e.g., `TEST_DB_NAME=vl_silks_test_db`).
   - `TestingConfig` **never** falls back to `vl_silks_db`. If `TEST_DB_NAME` is missing or configured to match `DB_NAME`, application startup under `TestingConfig` immediately raises a descriptive `RuntimeError`.
   - All runtime database queries within `create_app('testing')` contexts verify they are connected to `TEST_DB_NAME`.

2. **Test Database Provisioning:**
   ```bash
   python database/setup_test_db.py
   ```
   This script creates `vl_silks_test_db` if it does not exist, applies `database/schema.sql`, and applies `database/seed.sql` without touching `vl_silks_db`.

3. **Running the Isolation Tests:**
   ```bash
   pytest tests/test_database_isolation.py -v
   ```
