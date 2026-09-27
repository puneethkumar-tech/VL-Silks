# Database Normalization Documentation

## VL Silks - Database Normalization Analysis (1NF to 3NF)

---

## 1. Executive Summary

**3NF normalization is demonstrated for the project schema.**

Database Normalization is the formal process of structuring a relational schema to minimize data redundancy, avoid insertion, update, and deletion anomalies, and maintain referential integrity. 

This document demonstrates how the 15 tables of the **VL Silks** database adhere to First Normal Form (1NF), Second Normal Form (2NF), and Third Normal Form (3NF), while clarifying the practical business design rationale for point-in-time financial audit snapshots.

---

## 2. First Normal Form (1NF)

### 1NF Rules:
1. Every attribute column must hold strictly **atomic** (indivisible, scalar) values.
2. There must be **no repeating groups** or multi-valued arrays within a single record.
3. Each table must have a unique identifier (**Primary Key**).

### Unnormalized Problem:
In a naive single-table spreadsheet or flat file, a garment sale might be stored with non-atomic lists:
```text
Unnormalized Sale:
(sale_id: 101, customer: "Priya", items: "Saree-Blue, Kurti-Red", quantities: "2, 1", prices: "4500.00, 1200.00")
```
*Anomalies:* Parsing individual items requires string splitting, querying item sales is slow and error-prone, and indexing individual garments is impossible.

### Demonstrated 1NF Resolution in VL Silks:
All repeating groups are decomposed into distinct relational child tables with atomic scalar attributes:
- `sales` (Header) $\rightarrow$ `sale_items` (Line Items: `sale_item_id PK`, `variant_id FK`, `quantity`, `unit_price`, `discount`, `total_price`)
- `purchases` (Header) $\rightarrow$ `purchase_items` (Line Items: `purchase_item_id PK`, `variant_id FK`, `quantity`, `unit_price`, `total_price`)
- `returns` (Header) $\rightarrow$ `return_items` (Line Items: `return_item_id PK`, `variant_id FK`, `quantity`, `unit_price`, `refund_amount`, `condition_status`)

Every column in all 15 tables uses atomic primitive data types (`INT`, `VARCHAR`, `DECIMAL(10,2)`, `DATE`, `TIMESTAMP`, `ENUM`).

---

## 3. Second Normal Form (2NF)

### 2NF Rules:
1. The table must satisfy **1NF**.
2. There must be **no partial functional dependencies** — no non-prime attribute may depend on a proper subset of any candidate key.

### Demonstrated 2NF Resolution in VL Silks:
In VL Silks, all 15 tables utilize **single-attribute surrogate primary keys** (`AUTO_INCREMENT INT`):
- `users`: `user_id` (PK)
- `categories`: `category_id` (PK)
- `products`: `product_id` (PK)
- `product_variants`: `variant_id` (PK)
- `suppliers`: `supplier_id` (PK)
- `purchases`: `purchase_id` (PK)
- `purchase_items`: `purchase_item_id` (PK)
- `customers`: `customer_id` (PK)
- `sales`: `sale_id` (PK)
- `sale_items`: `sale_item_id` (PK)
- `payments`: `payment_id` (PK)
- `credit_transactions`: `transaction_id` (PK)
- `stock_movements`: `movement_id` (PK)
- `returns`: `return_id` (PK)
- `return_items`: `return_item_id` (PK)

Because every primary key consists of exactly one column, a proper subset of a primary key cannot exist. Therefore, partial functional dependency is mathematically impossible, and all tables **fully satisfy 2NF**.

---

## 4. Third Normal Form (3NF)

### 3NF Rules:
1. The table must satisfy **2NF**.
2. There must be **no transitive functional dependencies** ($X \rightarrow Y$ and $Y \rightarrow Z$ where $Z$ is a non-prime attribute depending on key $X$ through non-key $Y$). Every non-prime attribute must depend *directly and only* on the candidate key.

### Demonstrated 3NF Decompositions in VL Silks:

#### 4.1 Products and Categories
- **Potential Transitive Dependency:** If category details were stored in `products`:
  $$\text{product\_id} \rightarrow \text{category\_name} \rightarrow \text{category\_description}$$
  Updating a category description would require updating every product in that category (Update Anomaly).
- **3NF Resolution:** Decomposed into:
  - `categories` (`category_id` PK, `category_name`, `description`, `status`)
  - `products` (`product_id` PK, `category_id` FK, `product_name`, `brand`, `material`, `description`, `status`)

#### 4.2 Products and Multi-Attribute Variants
- **Potential Transitive Dependency:** Storing size, color, SKU, cost price, selling price, and stock in `products` would duplicate product name, material, and brand for every variant.
- **3NF Resolution:** Decomposed into:
  - Base product: `products` (`product_id` PK, `product_name`, `brand`, `material`)
  - Variant lines: `product_variants` (`variant_id` PK, `product_id` FK, `sku`, `size`, `color`, `purchase_price`, `selling_price`, `stock_quantity`, `minimum_stock`)

#### 4.3 Customers and Invoices
- **Potential Transitive Dependency:** Storing customer phone, email, address, or credit limit inside `sales` invoices:
  $$\text{sale\_id} \rightarrow \text{customer\_id} \rightarrow \text{customer\_phone}$$
- **3NF Resolution:** Decomposed into:
  - `customers` (`customer_id` PK, `customer_name`, `phone`, `email`, `address`, `credit_limit`)
  - `sales` (`sale_id` PK, `customer_id` FK, `invoice_number`, `sale_date`, `payment_method`, ...)

---

## 5. Design Rationale: Transactional Snapshots vs Derived Redundancy

In enterprise ERP and retail billing systems, certain financial snapshot attributes are deliberately preserved at the time of transaction:

1. **`sales.total_amount` and `sales.balance_amount`:**
   - *Rationale:* An invoice is a legally binding point-in-time financial contract. Preserving the exact billed total and balance at the time of sale ensures financial auditability even if catalog prices or tax rules change later.
2. **`sale_items.unit_price` and `purchase_items.unit_price`:**
   - *Rationale:* Preserves the exact historical price charged on the date of transaction, decoupled from future price revisions in `product_variants`.
3. **`credit_transactions.running_balance`:**
   - *Rationale:* Provides an immutable sequential audit ledger for fast statement rendering and mathematical dispute reconciliation.

These point-in-time snapshot columns represent historical transaction facts rather than volatile redundant attributes.

---

## 6. Normalization Summary Table

| Table Name | Normal Form | Key Determinant | Demonstrated Normalization Features |
|---|---|---|---|
| `users` | **3NF** | `user_id` (PK), `email` (UK) | Atomic fields, independent user entity, no transitive dependencies |
| `categories` | **3NF** | `category_id` (PK), `category_name` (UK) | Decomposed from products to isolate category descriptions |
| `products` | **3NF** | `product_id` (PK) | Isolated base garment definition; references category via FK |
| `product_variants` | **3NF** | `variant_id` (PK), `sku` (UK) | Decomposed from products; isolates size, color, SKU, and stock |
| `suppliers` | **3NF** | `supplier_id` (PK) | Master supplier directory isolated from purchase invoices |
| `purchases` | **3NF** | `purchase_id` (PK) | Inward procurement header; references supplier via FK |
| `purchase_items` | **3NF** | `purchase_item_id` (PK) | Decomposed line items; eliminates repeating purchase groups |
| `customers` | **3NF** | `customer_id` (PK), `phone` (UK) | Isolated customer profile; independent credit limit |
| `sales` | **3NF** | `sale_id` (PK), `invoice_number` (UK) | Invoice header; references customer and billing user via FK |
| `sale_items` | **3NF** | `sale_item_id` (PK) | Decomposed line items; eliminates repeating sale groups |
| `payments` | **3NF** | `payment_id` (PK) | Discrete payment receipts linked to customer and sale |
| `credit_transactions` | **3NF** | `transaction_id` (PK) | Immutable Udhaar ledger with chronological audit trail |
| `stock_movements` | **3NF** | `movement_id` (PK) | Immutable inventory change log capturing all stock deltas |
| `returns` | **3NF** | `return_id` (PK) | Return/exchange header linked to original sale |
| `return_items` | **3NF** | `return_item_id` (PK) | Decomposed return lines with itemized condition status |
