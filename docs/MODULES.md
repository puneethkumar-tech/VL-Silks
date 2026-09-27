# Module Specifications
## VL Silks - Subsystem Modules, Endpoints & Services Documentation
---
## 1. Authentication & Access Control Module
- **Blueprint:** `backend/routes/auth.py`
- **Service:** `backend/services/auth_service.py`
- **Templates:** `login.html`
- **Key Features:**
  - Secure session creation with Werkzeug scrypt password verification.
  - Role-Based Access Control decorators (`@login_required`, `@admin_required`).
  - Active user verification on every authenticated request.
- **Endpoints:**
  - `GET/POST /login` - User login page and credential submission.
  - `GET /logout` - Session invalidation and redirect.
  - `GET /api/auth/me` - JSON endpoint returning current session identity and role.
---
## 2. Dashboard & Analytics Module
- **Blueprint:** `backend/routes/dashboard.py`
- **Service:** `backend/services/dashboard_service.py`
- **Templates:** `dashboard.html`
- **Key Features:**
  - Real-time business KPI aggregation (Today's Sales, Monthly Revenue, Credit Outstanding, Low Stock Items).
  - Top 5 selling garment variants by volume and revenue.
  - Chart.js integration for 6-month monthly revenue trend and category sales distribution.
  - Quick action links and low stock alerts.
- **Endpoints:**
  - `GET /dashboard` - Render administrative/staff dashboard.
  - `GET /api/dashboard/summary` - Live JSON KPI stats (today sales, month revenue, credit outstanding).
  - `GET /api/dashboard/recent-sales` - JSON list of latest invoices.
  - `GET /api/dashboard/low-stock` - JSON list of variants below minimum stock threshold.
  - `GET /api/dashboard/monthly-sales` - JSON data for monthly revenue trend chart.
  - `GET /api/dashboard/top-products` - JSON list of top-selling garments.
  - `GET /api/dashboard/category-distribution` - JSON data for category revenue distribution donut chart.
---
## 3. Product & Category Management Module
- **Blueprints:** `backend/routes/products.py`, `backend/routes/categories.py`
- **Services:** `backend/services/product_service.py`, `backend/services/category_service.py`
- **Templates:** `products/index.html`, `products/create.html`, `products/edit.html`, `products/view.html`, `categories/index.html`
- **Key Features:**
  - Multi-variant garment catalog creation (Product header + Size/Color/SKU lines).
  - Search and filter by category, brand, material, and status.
  - Automatic SKU generation and barcode indexing.
  - Low-stock threshold configuration per variant.
- **Endpoints:**
  - `GET /products` - List products with variant count and aggregate stock.
  - `GET/POST /products/create` - Create new product and initial variants (Admin only).
  - `GET/POST /products/<id>/edit` - Modify product metadata and variant details (Admin only).
  - `GET /products/<id>` - View complete product profile and variant matrix.
  - `GET /api/products/search` - Real-time JSON search for POS autocomplete.
  - `GET/POST /categories` - Category list and add new category.
---
## 4. Supplier & Purchase Inward Module
- **Blueprints:** `backend/routes/suppliers.py`, `backend/routes/purchases.py`
- **Services:** `backend/services/supplier_service.py`, `backend/services/purchase_service.py`
- **Templates:** `suppliers/index.html`, `suppliers/create.html`, `purchases/index.html`, `purchases/create.html`, `purchases/view.html`
- **Key Features:**
  - Supplier master registry with phone, GSTIN, and contact details.
  - Purchase order entry recording supplier invoice number, items, costs, discounts, and taxes.
  - Atomic stock quantity increment on confirmation with automatic `stock_movements` audit entry (`PURCHASE`).
- **Endpoints:**
  - `GET /suppliers` - Supplier directory.
  - `POST /suppliers/create` - Register new supplier.
  - `GET /purchases` - Inward purchase invoice history.
  - `GET/POST /purchases/create` - Enter new inward purchase bill (Admin only).
  - `GET /purchases/<id>` - View purchase invoice details and line items.
---
## 5. Inventory & Stock Movement Audit Module
- **Blueprint:** `backend/routes/inventory.py`
- **Service:** `backend/services/inventory_service.py`
- **Templates:** `inventory/index.html`, `inventory/movements.html`, `inventory/adjust.html`
- **Key Features:**
  - Real-time stock overview with low-stock highlighting.
  - Comprehensive stock movement ledger tracking all 5 movement types (`PURCHASE`, `SALE`, `CUSTOMER_RETURN`, `DAMAGE`, `ADJUSTMENT`).
  - Admin stock adjustment workflow with mandatory reason logging and non-negative stock enforcement.
- **Endpoints:**
  - `GET /inventory` - Current stock levels across all variants.
  - `GET /inventory/movements` - Chronological stock movements audit log.
  - `POST /inventory/adjust` - Manual inventory correction (Admin only).
---
## 6. Point of Sale (POS) Billing Module
- **Blueprint:** `backend/routes/sales.py`
- **Service:** `backend/services/sale_service.py`
- **Templates:** `sales/index.html`, `sales/pos.html`, `sales/view.html`
- **Key Features:**
  - High-speed POS interface with instant variant search and barcode support.
  - Dynamic client-side cart with server-side validation.
  - Support for 5 payment methods: `CASH`, `UPI`, `CARD`, `CREDIT` (Udhaar), and `SPLIT`.
  - Credit limit check: validates that customer credit balance does not exceed authorized limit.
  - Atomic invoice generation (`SALE-YYYY-NNNN`), stock deduction, payment recording, and credit ledger debit.
- **Endpoints:**
  - `GET /pos` - Render POS checkout counter.
  - `POST /api/pos/checkout` - Process sale transaction atomically.
  - `GET /sales` - Sales invoice history.
  - `GET /sales/<id>` - View itemized invoice receipt.
---
## 7. Customer & Credit / Udhaar Management Module
- **Blueprints:** `backend/routes/customers.py`, `backend/routes/credit.py`
- **Services:** `backend/services/customer_service.py`, `backend/services/credit_service.py`
- **Templates:** `customers/index.html`, `customers/profile.html`, `credit/index.html`, `credit/view.html`, `credit/settle.html`
- **Key Features:**
  - Customer registry with phone lookup and credit limit assignment.
  - Authoritative Udhaar credit ledger tracking `CREDIT_SALE`, `PAYMENT`, and `RETURN_REFUND`.
  - Outstanding balance calculation strictly from ledger sum.
  - Partial and full credit settlement payment collection with overpayment protection.
- **Endpoints:**
  - `GET /customers` - Customer list with search by name/phone.
  - `POST /customers/create` - Register customer.
  - `GET /credit` - Outstanding credit customer list and aggregate receivables.
  - `GET /credit/<customer_id>` - Customer credit profile and chronological ledger.
  - `POST /credit/<customer_id>/pay` - Record credit settlement payment.
---
## 8. Credit PDF Statement Generator Module
- **Blueprint:** `backend/routes/pdf.py`
- **Service:** `backend/services/pdf_service.py`
- **Key Features:**
  - Server-side generation of professional A4 PDF credit statements using ReportLab.
  - Branded VL Silks header, customer details, date range filter, chronological ledger table, and summary boxes.
  - Read-only generation with zero database side-effects.
- **Endpoints:**
  - `GET /credit/<customer_id>/statement` - Generate and stream customer PDF credit statement.
---
## 9. Returns & Exchanges Module
- **Blueprint:** `backend/routes/returns.py`
- **Service:** `backend/services/return_service.py`
- **Templates:** `returns/index.html`, `returns/create.html`, `returns/exchange.html`, `returns/view.html`
- **Key Features:**
  - Return garments against existing sale invoices with over-return prevention.
  - Condition classification: `RESTOCKABLE` (stock restored + `CUSTOMER_RETURN` movement) vs `DAMAGED` (stock not restored + `DAMAGE` audit movement).
  - Refund disbursement modes: `CASH` or `CREDIT_ADJUSTMENT` (`RETURN_REFUND` in credit ledger).
  - Garment exchange workflow: swap returned items for replacement variants with automatic price difference reconciliation.
- **Endpoints:**
  - `GET /returns` - List all return transactions.
  - `GET/POST /returns/create` - Process return against invoice.
  - `GET/POST /returns/exchange` - Process garment exchange.
  - `GET /returns/<id>` - View return/exchange audit record.
---
## 10. Business Reports Module
- **Blueprint:** `backend/routes/reports.py`
- **Service:** `backend/services/report_service.py`
- **Templates:** `reports/sales.html`, `reports/purchases.html`, `reports/inventory.html`, `reports/credit_aging.html`, `reports/profit.html`
- **Key Features:**
  - 5 comprehensive business reports with custom date range filters:
    1. **Sales Report:** Revenue, discounts, taxes, payment method breakdown.
    2. **Purchase Report:** Procurement volume, costs, supplier payable breakdown.
    3. **Inventory Valuation Report:** Stock quantities, asset cost value, expected retail value.
    4. **Credit Aging Report:** Receivables bucketed into 0-30 days, 31-60 days, 61-90 days, 90+ days.
    5. **Profit Report:** Gross margin per garment variant (`Selling Price - Cost Price`).
  - One-click CSV export for all reports.
- **Endpoints:**
  - `GET /reports/sales` & `GET /reports/sales/csv`
  - `GET /reports/purchases` & `GET /reports/purchases/csv`
  - `GET /reports/inventory` & `GET /reports/inventory/csv`
  - `GET /reports/credit-aging` & `GET /reports/credit-aging/csv`
  - `GET /reports/profit` & `GET /reports/profit/csv`
