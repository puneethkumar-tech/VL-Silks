# Data Flow Diagram (DFD)
## VL Silks - Garment Shop Inventory, Sales & Credit Management System
---
## 1. Context Level (Level 0) DFD
The Level 0 DFD portrays the entire VL Silks system as a single process interacting with all external entities:
```
                            +--------------------+
                            |       ADMIN        |
                            +---------+----------+
                                      | Login credentials,
                                      | Catalog definitions,
                                      | Inward purchase bills,
                                      | Stock adjustments,
                                      | Report queries
                                      v
+----------+ Login/Sales    +------------------------------------+   Reports, PDFs
|  STAFF   +--------------->|                                    +------------------> Output Reports
+----------+ Returns/Udhaar |   VL SILKS GARMENT MANAGEMENT      |                    & Statements
                            |             SYSTEM                 |
+----------+ Stock delivery |   (Flask + MySQL Web App)          |
| SUPPLIER +--------------->|                                    |
+----------+ & Invoices     +-----------------+------------------+
                                              |
                                              | POS Invoices,
                                              | Udhaar balances,
                                              | Credit Statements
                                              v
                                    +--------------------+
                                    |      CUSTOMER      |
                                    +--------------------+
```
---
## 2. Level 1 DFD - Major System Subsystems
```
                                  USER (Admin / Staff)
                                           |
                                           v
                             +---------------------------+
                             | 1.0 Authentication & RBAC |
                             +-------------+-------------+
                                           | Validated Session
                                           v
        +----------------------------------+----------------------------------+
        |                  |               |                |                 |
        v                  v               v                v                 v
+---------------+  +---------------+  +----------+  +---------------+  +---------------+
| 2.0 Catalog & |  | 3.0 Purchase  |  | 4.0 POS  |  | 5.0 Udhaar    |  | 6.0 Returns   |
| Inventory     |  | Inward        |  | Sales &  |  | & Settlement  |  | & Exchanges   |
| Management    |  | Management    |  | Billing  |  | Management    |  | Management    |
+-------+-------+  +-------+-------+  +----+-----+  +-------+-------+  +-------+-------+
        |                  |               |                |                  |
        v                  v               v                v                  v
  [categories]       [suppliers]        [sales]        [customers]         [returns]
  [products]         [purchases]        [sale_items]   [credit_            [return_items]
  [product_          [purchase_items]   [payments]      transactions]      [stock_
   variants]         [stock_            [stock_        [payments]           movements]
  [stock_             movements]         movements]
   movements]
        |                  |               |                |                  |
        +------------------+---------------+----------------+------------------+
                                           |
                                           v
                             +---------------------------+
                             | 7.0 Business Reports &    |
                             | Analytics Engine          |
                             +---------------------------+
                                           |
                                           v
                             Sales / Purchase / Valuation /
                             Credit Aging / Profit CSV & PDFs
```
---
## 3. Level 2 DFD - Core Transaction Workflows
### 3.1 Point of Sale (POS) Billing & Credit Deduction
```
Staff Input (Items, Customer, Payment Mode)
  │
  ├─► [Validate Customer & Variant Quantities]
  │     │
  │     ├─► Check variant stock >= requested quantity (Reject if insufficient)
  │     └─► Check if Credit Sale: customer selected & (balance + sale) <= credit_limit
  │
  ├─► [Compute Financials via Decimal Precision]
  │     │
  │     └─► subtotal = sum(qty * price), line discounts, tax, total_amount
  │
  ├─► [Atomic MySQL Transaction Commit]
  │     ├─► INSERT INTO sales (...)
  │     ├─► INSERT INTO sale_items (...)
  │     ├─► UPDATE product_variants SET stock_quantity = stock_quantity - qty
  │     ├─► INSERT INTO stock_movements (movement_type='SALE')
  │     ├─► IF paid_amount > 0: INSERT INTO payments (...)
  │     └─► IF balance_amount > 0: INSERT INTO credit_transactions (type='CREDIT_SALE')
  │
  └─► Return JSON success & Invoice Preview (SALE-YYYY-NNNN)
```
### 3.2 Customer Return & Garment Exchange
```
Staff Input (Sale ID, Return Items, Conditions, Exchange Items)
  │
  ├─► [Validation Phase]
  │     ├─► Verify sale exists and return quantities <= (original_sold - already_returned)
  │     └─► Verify replacement items have sufficient stock
  │
  ├─► [Atomic Transaction Execution]
  │     ├─► INSERT INTO returns (sale_id, refund_type, total_refund_amount)
  │     ├─► INSERT INTO return_items (return_id, condition_status, refund_amount)
  │     ├─► IF condition_status == 'RESTOCKABLE':
  │     │     ├─► UPDATE product_variants SET stock_quantity = stock_quantity + qty
  │     │     └─► INSERT INTO stock_movements (movement_type='CUSTOMER_RETURN')
  │     ├─► IF condition_status == 'DAMAGED':
  │     │     └─► INSERT INTO stock_movements (movement_type='DAMAGE', stock unincremented)
  │     ├─► IF refund_type == 'CREDIT_ADJUSTMENT':
  │     │     └─► INSERT INTO credit_transactions (type='RETURN_REFUND', negative debit)
  │     └─► IF Exchange requested:
  │           ├─► Deduct new variant stock + INSERT movement_type='SALE'
  │           └─► Reconcile price_difference (Cash / Udhaar adjustment)
  │
  └─► Commit Transaction & Return Summary
```
