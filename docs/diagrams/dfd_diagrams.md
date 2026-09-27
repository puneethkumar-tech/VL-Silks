# Data Flow Diagrams (DFD)

## VL Silks - Data Flow Diagrams Reference

---

## 1. Level 0 DFD (Context Level)

```text
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

## 2. Level 1 DFD (Subsystem Decomposition)

```text
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

## 3. Level 2 DFD (POS Billing & Return Workflows)

```text
3.1 POS Checkout:
Staff Input (Items, Customer, Payment Mode)
  |
  +--> Validate Variant Stock & Customer Credit Limit
  |
  +--> Compute Financials via Decimal Arithmetic (Subtotal, Discounts, Total, Balance)
  |
  +--> Atomic Transaction:
         - INSERT INTO sales
         - INSERT INTO sale_items
         - UPDATE product_variants (stock deduction)
         - INSERT INTO stock_movements (SALE audit)
         - INSERT INTO payments (if cash/card/upi paid)
         - INSERT INTO credit_transactions (if Udhaar credit)
  |
  +--> Output Invoice (SALE-YYYY-NNNN)

3.2 Customer Returns & Garment Exchanges:
Staff Input (Sale ID, Return Items, Conditions, Exchange Items)
  |
  +--> Validate Return Quantity <= (Original Sold - Prior Returns)
  |
  +--> Atomic Transaction:
         - INSERT INTO returns & return_items
         - IF RESTOCKABLE: UPDATE product_variants (stock increment) + stock_movements (CUSTOMER_RETURN)
         - IF DAMAGED: stock_movements (DAMAGE, no shelf restock)
         - IF CREDIT_ADJUSTMENT: credit_transactions (RETURN_REFUND)
         - IF EXCHANGE: Deduct new variant stock + Reconcile price difference
  |
  +--> Output Return Voucher & Balance Summary
```
