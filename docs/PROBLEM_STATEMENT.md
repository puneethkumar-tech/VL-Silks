# Problem Statement
## VL Silks - Garment Shop Inventory, Sales & Credit Management System
---
## 1. Problem Description
Traditional garment shops in India, especially traditional silk saree and ethnic wear retailers like VL Silks, rely heavily on manual paper ledgers, printed bill books, and mental accounting. This manual operation gives rise to several critical operational challenges:
### 1.1 Inaccurate Manual Stock Tracking
Garments vary by fabric, style, design, color, and size. Tracking stock levels in physical registers often results in missed entries during peak hours or festival sales. Discrepancies between physical inventory and book records lead to lost sales or unfulfillable promises.
### 1.2 Multi-Variant Complexity
A single garment product (such as a *Kanjivaram Pure Silk Saree*) comes in numerous color, weave, and border variants, each with distinct SKUs, barcodes, purchase costs, and selling prices. Physical registers cannot efficiently index or search multi-attribute variants in real time.
### 1.3 Inefficient Billing & Point-of-Sale
Handwritten invoices require staff to manually look up prices, calculate line discounts, and sum totals by hand. This leads to long customer checkout queues, calculation errors, lack of auditability, and lost tax records.
### 1.4 Credit / Udhaar Bookkeeping Vulnerabilities
A significant portion of retail sales in traditional Indian apparel retail involves trusted customer credit ("Udhaar"). In manual systems:
- Credit balances are maintained across disparate notebooks.
- Payments, partial settlements, and returns are inconsistently deducted.
- Customers dispute unverified balances due to lack of itemized transaction history.
- Shops lack visibility into credit aging and overdue balances.
### 1.5 Unstructured Inward Purchase & Supplier Management
Stock procurement from multiple weaving centers and suppliers involves supplier bills that are filed in paper folders. Without automated stock increments and cost tracking, inventory valuation and supplier payable tracking become difficult.
### 1.6 Complex Returns and Exchanges
Garment exchanges (swapping one size/color for another) and customer returns involve complex stock adjustments (differentiating restockable items from damaged items) and financial adjustments (cash refund vs. Udhaar credit adjustment). Without a transactional system, returns frequently cause ledger inaccuracies.
### 1.7 Absence of Business Analytics & Reporting
Shop owners cannot easily compute daily gross sales, monthly margins, inventory valuation, or top-selling product categories without days of manual data compilation.
---
## 2. Existing System vs. Proposed System
| Feature / Aspect | Existing Manual System | Proposed VL Silks System |
|---|---|---|
| **Inventory Tracking** | Physical stock registers; delayed updates | Real-time automated stock updates with full movement audit trail |
| **Garment Variants** | Single line items; size/color untracked | Multi-variant catalog (Size, Color, SKU, Barcode, Thresholds) |
| **POS Billing** | Handwritten paper receipts; manual arithmetic | Fast POS billing with instant search, auto-totals, and payment splits |
| **Payment Modes** | Cash only or untracked notes | Cash, UPI, Card, Udhaar (Credit), and Split payments |
| **Credit (Udhaar)** | Handwritten notebooks; frequent balance disputes | Authoritative running transactional ledger (`credit_transactions`) |
| **Credit Statements** | Verbal summary or notebook photos | Professional branded A4 PDF statements with full audit trail |
| **Returns & Exchanges** | Manual stock edits; prone to forgotten entries | Atomic return/exchange workflows with condition checks & ledger balance sync |
| **Access Control** | No security; anyone can alter entries | Role-based authentication (Admin vs. Staff) with session protection |
| **Reporting** | Manual end-of-year calculation | Instant Sales, Purchases, Valuation, Credit Aging, and Profit reports (CSV) |
---
## 3. Project Objectives
1. **Centralized Catalog & Variant Management:** Provide full CRUD for categories, products, and multi-attribute variants with SKU/barcode indexing and minimum stock alerts.
2. **Real-Time Stock Auditing:** Maintain an immutable `stock_movements` ledger capturing every inventory addition, deduction, return, damage, and adjustment.
3. **Automated Purchase Processing:** Record inward supplier invoices, updating stock and audit movements atomically.
4. **Fast POS & Multi-Mode Billing:** Support rapid billing, line discounts, tax handling, and diverse payment options (Cash, UPI, Card, Credit, Split).
5. **Authoritative Udhaar Ledger:** Implement an immutable credit transaction log (`CREDIT_SALE`, `PAYMENT`, `RETURN_REFUND`) with automated balance calculation and overpayment rejection.
6. **ReportLab PDF Statement Generator:** Generate downloadable, formatted A4 customer credit statements.
7. **Atomic Returns & Garment Exchanges:** Handle restockable vs. damaged item returns and garment swaps with price differences in single atomic database transactions.
8. **Business Intelligence & Dashboards:** Deliver live metrics (Today's Sales, Monthly Revenue, Credit Outstanding, Low Stock alerts) and interactive visualizations.
9. **Decision-Ready Reports:** Produce downloadable CSV and printable reports for Sales, Purchases, Inventory Valuation, Credit Aging, and Gross Profit.
10. **Enterprise Security & Reliability:** Enforce role-based access, parameterized SQL queries against SQL injection, scrypt password hashing, and MySQL InnoDB transactional integrity.
