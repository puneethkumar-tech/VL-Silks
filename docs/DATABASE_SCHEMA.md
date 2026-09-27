# Database Schema Reference
## VL Silks - Relational Database Schema Specification (15 Tables)
**Database:** `vl_silks_db` | **Engine:** `InnoDB` | **Charset:** `utf8mb4` | **Collation:** `utf8mb4_unicode_ci`
---
## Table 1: `users`
System user accounts for staff and administrators.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `user_id` | INT | PK, AUTO_INCREMENT | Unique user identifier |
| `name` | VARCHAR(100) | NOT NULL | User's full name |
| `email` | VARCHAR(100) | NOT NULL, UNIQUE | User login email address |
| `password_hash` | VARCHAR(255) | NOT NULL | Werkzeug scrypt password hash |
| `role` | ENUM('ADMIN','STAFF') | NOT NULL, DEFAULT 'STAFF' | Access role |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Account status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update timestamp |
---
## Table 2: `categories`
Garment categories (e.g., Silk Sarees, Cotton Dhotis, Kurtis).
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `category_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `category_name` | VARCHAR(100) | NOT NULL, UNIQUE | Category title |
| `description` | TEXT | NULL | Descriptive notes |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 3: `products`
Base garment definitions.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `product_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `category_id` | INT | NOT NULL, FK -> `categories.category_id` (RESTRICT) | Parent category |
| `product_name` | VARCHAR(150) | NOT NULL | Product name |
| `brand` | VARCHAR(100) | DEFAULT 'VL Silks' | Brand/label |
| `material` | VARCHAR(100) | NULL | Fabric material (e.g., Pure Kanjivaram Silk) |
| `description` | TEXT | NULL | Product description |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 4: `product_variants`
Size and color variations of base products with pricing and inventory.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `variant_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `product_id` | INT | NOT NULL, FK -> `products.product_id` (RESTRICT) | Base product link |
| `sku` | VARCHAR(50) | NOT NULL, UNIQUE | Unique Stock Keeping Unit |
| `size` | VARCHAR(20) | NOT NULL | Size (e.g., Free Size, L, XL, 6.2m) |
| `color` | VARCHAR(50) | NOT NULL | Color/Pattern (e.g., Royal Blue & Gold) |
| `purchase_price` | DECIMAL(10,2) | NOT NULL | Procurement cost per unit |
| `selling_price` | DECIMAL(10,2) | NOT NULL | Retail selling price per unit |
| `stock_quantity` | INT | NOT NULL, DEFAULT 0, CHECK (`stock_quantity` >= 0) | Real-time stock count |
| `minimum_stock` | INT | NOT NULL, DEFAULT 5 | Low-stock alert threshold |
| `barcode` | VARCHAR(50) | NULL, UNIQUE | Scannable EAN/UPC barcode |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Variant status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 5: `suppliers`
Wholesalers, weavers, and garment suppliers.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `supplier_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `supplier_name` | VARCHAR(150) | NOT NULL | Supplier business name |
| `contact_person` | VARCHAR(100) | NULL | Representative name |
| `phone` | VARCHAR(20) | NOT NULL | Contact telephone |
| `email` | VARCHAR(100) | NULL | Email address |
| `address` | TEXT | NULL | Physical address / City |
| `gst_number` | VARCHAR(20) | NULL | Indian GSTIN number |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 6: `purchases`
Inward supplier procurement orders.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `purchase_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `supplier_id` | INT | NOT NULL, FK -> `suppliers.supplier_id` (RESTRICT) | Supplier |
| `invoice_number` | VARCHAR(50) | NOT NULL | Supplier's invoice reference |
| `purchase_date` | DATE | NOT NULL | Date of procurement |
| `subtotal` | DECIMAL(12,2) | NOT NULL | Sum of line totals |
| `discount` | DECIMAL(10,2) | DEFAULT 0.00 | Total purchase discount |
| `tax` | DECIMAL(10,2) | DEFAULT 0.00 | Inward GST/tax amount |
| `total` | DECIMAL(12,2) | NOT NULL | Net invoice payable |
| `payment_status` | ENUM('PAID','PENDING','PARTIAL') | DEFAULT 'PENDING' | Supplier settlement status |
| `notes` | TEXT | NULL | Procurement notes |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | User who entered purchase |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 7: `purchase_items`
Line items for inward purchase invoices.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `purchase_item_id`| INT | PK, AUTO_INCREMENT | Primary key |
| `purchase_id` | INT | NOT NULL, FK -> `purchases.purchase_id` (CASCADE) | Purchase invoice link |
| `variant_id` | INT | NOT NULL, FK -> `product_variants.variant_id` (RESTRICT)| Purchased variant |
| `quantity` | INT | NOT NULL | Units received |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Cost price per unit |
| `total_price` | DECIMAL(12,2) | NOT NULL | Line total (`quantity * unit_price`) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
---
## Table 8: `customers`
Retail and credit customers.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `customer_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `customer_name` | VARCHAR(100) | NOT NULL | Customer full name |
| `phone` | VARCHAR(20) | NOT NULL, UNIQUE | Primary mobile number |
| `email` | VARCHAR(100) | NULL | Customer email |
| `address` | TEXT | NULL | Address/City |
| `credit_limit` | DECIMAL(10,2) | DEFAULT 0.00 | Maximum allowed Udhaar balance |
| `status` | ENUM('ACTIVE','INACTIVE') | NOT NULL, DEFAULT 'ACTIVE' | Account status |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 9: `sales`
Customer sales receipts and invoices.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `sale_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `customer_id` | INT | NULL, FK -> `customers.customer_id` (SET NULL) | Customer (NULL for walk-in) |
| `invoice_number` | VARCHAR(50) | NOT NULL, UNIQUE | Generated invoice number (`SALE-YYYY-NNNN`) |
| `sale_date` | DATE | NOT NULL | Date of sale |
| `subtotal` | DECIMAL(12,2) | NOT NULL | Pre-discount sum |
| `discount` | DECIMAL(10,2) | DEFAULT 0.00 | Invoice-level discount |
| `tax` | DECIMAL(10,2) | DEFAULT 0.00 | Applicable tax amount |
| `total_amount` | DECIMAL(12,2) | NOT NULL | Net payable |
| `paid_amount` | DECIMAL(12,2) | NOT NULL | Amount received at counter |
| `balance_amount` | DECIMAL(12,2) | NOT NULL | Amount on credit (`total_amount - paid_amount`) |
| `payment_method` | ENUM('CASH','UPI','CARD','CREDIT','SPLIT') | NOT NULL | Payment mechanism |
| `payment_status` | ENUM('PAID','PENDING','PARTIAL') | NOT NULL | Settlement state |
| `notes` | TEXT | NULL | Sale notes |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | Billing staff ID |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Update timestamp |
---
## Table 10: `sale_items`
Itemized garment lines in sales invoices.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `sale_item_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `sale_id` | INT | NOT NULL, FK -> `sales.sale_id` (CASCADE) | Invoice header link |
| `variant_id` | INT | NOT NULL, FK -> `product_variants.variant_id` (RESTRICT)| Sold garment variant |
| `quantity` | INT | NOT NULL | Quantity sold |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Selling price per unit |
| `discount` | DECIMAL(10,2) | DEFAULT 0.00 | Line item discount |
| `total_price` | DECIMAL(12,2) | NOT NULL | Line net total |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
---
## Table 11: `payments`
Counter payments and customer credit settlements.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `payment_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `customer_id` | INT | NOT NULL, FK -> `customers.customer_id` (RESTRICT) | Paying customer |
| `sale_id` | INT | NULL, FK -> `sales.sale_id` (SET NULL) | Specific sale if directly linked |
| `amount` | DECIMAL(10,2) | NOT NULL | Payment amount received |
| `payment_method` | ENUM('CASH','UPI','CARD','BANK_TRANSFER') | NOT NULL | Payment channel |
| `payment_date` | DATE | NOT NULL | Date payment received |
| `reference_number`| VARCHAR(100) | NULL | Transaction ID / UPI Ref |
| `notes` | TEXT | NULL | Payment notes |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | Staff recording payment |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record timestamp |
---
## Table 12: `credit_transactions`
Authoritative Udhaar ledger for customer credit accounting.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `transaction_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `customer_id` | INT | NOT NULL, FK -> `customers.customer_id` (RESTRICT) | Customer account |
| `sale_id` | INT | NULL, FK -> `sales.sale_id` (SET NULL) | Associated sale |
| `payment_id` | INT | NULL, FK -> `payments.payment_id` (SET NULL) | Associated settlement payment |
| `transaction_type`| ENUM('CREDIT_SALE','PAYMENT','RETURN_REFUND')| NOT NULL | Ledger entry classification |
| `amount` | DECIMAL(10,2) | NOT NULL | Transaction value |
| `running_balance` | DECIMAL(10,2) | NOT NULL | Balance after this transaction |
| `transaction_date`| DATE | NOT NULL | Transaction date |
| `notes` | TEXT | NULL | Descriptive details |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | User creating entry |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Audit timestamp |
---
## Table 13: `stock_movements`
Complete immutable inventory movement audit trail.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `movement_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `variant_id` | INT | NOT NULL, FK -> `product_variants.variant_id` (RESTRICT)| Variant affected |
| `movement_type` | ENUM('PURCHASE','SALE','CUSTOMER_RETURN','DAMAGE','ADJUSTMENT') | NOT NULL | Reason for stock change |
| `quantity` | INT | NOT NULL | Delta (+ for inward, - for outward) |
| `reference_type` | ENUM('PURCHASE','SALE','RETURN','ADJUSTMENT') | NULL | Source transaction type |
| `reference_id` | INT | NULL | Polymorphic ID to purchase/sale/return |
| `notes` | TEXT | NULL | Movement remarks |
| `movement_date` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp of stock change |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | User who initiated movement |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
---
## Table 14: `returns`
Customer return and exchange headers.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `return_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `sale_id` | INT | NOT NULL, FK -> `sales.sale_id` (RESTRICT) | Original invoice link |
| `customer_id` | INT | NULL, FK -> `customers.customer_id` (SET NULL) | Customer |
| `return_date` | DATE | NOT NULL | Date return processed |
| `return_reason` | TEXT | NULL | Customer reason for return |
| `total_refund_amount`| DECIMAL(10,2) | NOT NULL, DEFAULT 0.00 | Total calculated refund |
| `refund_type` | ENUM('CASH','CREDIT_ADJUSTMENT','EXCHANGE') | NOT NULL | Refund disbursement mode |
| `created_by` | INT | NOT NULL, FK -> `users.user_id` (RESTRICT) | Staff processing return |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
---
## Table 15: `return_items`
Individual items returned within a return transaction.
| Column | Data Type | Constraints | Description |
|---|---|---|---|
| `return_item_id` | INT | PK, AUTO_INCREMENT | Primary key |
| `return_id` | INT | NOT NULL, FK -> `returns.return_id` (CASCADE) | Parent return header |
| `sale_item_id` | INT | NULL, FK -> `sale_items.sale_item_id` (SET NULL) | Original sale item line |
| `variant_id` | INT | NOT NULL, FK -> `product_variants.variant_id` (RESTRICT)| Returned garment variant |
| `quantity` | INT | NOT NULL | Number of units returned |
| `unit_price` | DECIMAL(10,2) | NOT NULL | Original billed price |
| `refund_amount` | DECIMAL(10,2) | NOT NULL | Refund amount (`quantity * unit_price`) |
| `condition_status`| ENUM('RESTOCKABLE','DAMAGED') | NOT NULL, DEFAULT 'RESTOCKABLE' | Stock disposition |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |
