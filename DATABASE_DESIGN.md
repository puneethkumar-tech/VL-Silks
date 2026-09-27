# VL Silks Database Design

The database uses a normalized 15-table relational architecture designed in MySQL 8.x for garment shop inventory, sales, variants, and customer credit ledger tracking.

---

## 15-Table Architecture

### 1. `users`
* `user_id` INT AUTO_INCREMENT PK
* `name` VARCHAR(100) NOT NULL
* `email` VARCHAR(100) NOT NULL UNIQUE
* `password_hash` VARCHAR(255) NOT NULL
* `role` ENUM('ADMIN', 'STAFF') NOT NULL DEFAULT 'STAFF'
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 2. `categories`
* `category_id` INT AUTO_INCREMENT PK
* `category_name` VARCHAR(100) NOT NULL UNIQUE
* `description` TEXT
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 3. `products` (Base Garments)
* `product_id` INT AUTO_INCREMENT PK
* `category_id` INT FK → categories(category_id)
* `product_name` VARCHAR(150) NOT NULL
* `brand` VARCHAR(100) DEFAULT 'VL Silks'
* `material` VARCHAR(100)
* `description` TEXT
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 4. `product_variants` (Specific Size/Color Combinations)
* `variant_id` INT AUTO_INCREMENT PK
* `product_id` INT FK → products(product_id)
* `sku` VARCHAR(50) NOT NULL UNIQUE
* `size` VARCHAR(30) NOT NULL
* `color` VARCHAR(50) NOT NULL
* `purchase_price` DECIMAL(10,2) NOT NULL
* `selling_price` DECIMAL(10,2) NOT NULL
* `stock_quantity` INT NOT NULL DEFAULT 0 (CHECK >= 0)
* `minimum_stock` INT NOT NULL DEFAULT 5
* `barcode` VARCHAR(100) UNIQUE
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 5. `suppliers`
* `supplier_id` INT AUTO_INCREMENT PK
* `supplier_name` VARCHAR(150) NOT NULL
* `contact_person` VARCHAR(100)
* `phone` VARCHAR(20) NOT NULL
* `email` VARCHAR(100)
* `address` TEXT
* `gst_number` VARCHAR(30)
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 6. `purchases` (Supplier Inward Invoices)
* `purchase_id` INT AUTO_INCREMENT PK
* `supplier_id` INT FK → suppliers(supplier_id)
* `invoice_number` VARCHAR(50) NOT NULL
* `purchase_date` DATE NOT NULL
* `subtotal` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `discount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `tax` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `total` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `payment_status` ENUM('PAID', 'PARTIAL', 'PENDING') NOT NULL DEFAULT 'PAID'
* `notes` TEXT
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 7. `purchase_items`
* `purchase_item_id` INT AUTO_INCREMENT PK
* `purchase_id` INT FK → purchases(purchase_id) ON DELETE CASCADE
* `variant_id` INT FK → product_variants(variant_id)
* `quantity` INT NOT NULL (CHECK > 0)
* `unit_price` DECIMAL(10,2) NOT NULL
* `total_price` DECIMAL(12,2) NOT NULL
* `created_at` TIMESTAMP

### 8. `customers`
* `customer_id` INT AUTO_INCREMENT PK
* `customer_name` VARCHAR(150) NOT NULL
* `phone` VARCHAR(20) NOT NULL UNIQUE
* `email` VARCHAR(100)
* `address` TEXT
* `credit_limit` DECIMAL(12,2) DEFAULT 25000.00
* `status` ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE'
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 9. `sales` (Customer Billing Invoices)
* `sale_id` INT AUTO_INCREMENT PK
* `customer_id` INT NULL FK → customers(customer_id) ON DELETE SET NULL
* `invoice_number` VARCHAR(50) NOT NULL UNIQUE
* `sale_date` DATE NOT NULL
* `subtotal` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `discount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `tax` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `total_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `paid_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `balance_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `payment_method` ENUM('CASH', 'UPI', 'CARD', 'CREDIT', 'SPLIT') NOT NULL DEFAULT 'CASH'
* `payment_status` ENUM('PAID', 'PARTIAL', 'CREDIT') NOT NULL DEFAULT 'PAID'
* `notes` TEXT
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP
* `updated_at` TIMESTAMP

### 10. `sale_items`
* `sale_item_id` INT AUTO_INCREMENT PK
* `sale_id` INT FK → sales(sale_id) ON DELETE CASCADE
* `variant_id` INT FK → product_variants(variant_id)
* `quantity` INT NOT NULL (CHECK > 0)
* `unit_price` DECIMAL(10,2) NOT NULL
* `discount` DECIMAL(10,2) NOT NULL DEFAULT 0.00
* `total_price` DECIMAL(12,2) NOT NULL
* `created_at` TIMESTAMP

### 11. `payments` (Credit Settlement Collections)
* `payment_id` INT AUTO_INCREMENT PK
* `customer_id` INT FK → customers(customer_id)
* `sale_id` INT NULL FK → sales(sale_id) ON DELETE SET NULL
* `amount` DECIMAL(12,2) NOT NULL (CHECK > 0)
* `payment_method` ENUM('CASH', 'UPI', 'CARD', 'BANK_TRANSFER') NOT NULL DEFAULT 'CASH'
* `payment_date` DATE NOT NULL
* `reference_number` VARCHAR(100)
* `notes` TEXT
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP

### 12. `credit_transactions` (Customer Udhaar Ledger)
* `transaction_id` INT AUTO_INCREMENT PK
* `customer_id` INT FK → customers(customer_id)
* `sale_id` INT NULL FK → sales(sale_id) ON DELETE SET NULL
* `payment_id` INT NULL FK → payments(payment_id) ON DELETE SET NULL
* `transaction_type` ENUM('CREDIT_SALE', 'PAYMENT', 'RETURN_REFUND', 'ADJUSTMENT') NOT NULL
* `amount` DECIMAL(12,2) NOT NULL
* `running_balance` DECIMAL(12,2) NULL
* `transaction_date` DATE NOT NULL
* `notes` TEXT
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP

### 13. `stock_movements` (Inventory Audit Trail)
* `movement_id` INT AUTO_INCREMENT PK
* `variant_id` INT FK → product_variants(variant_id)
* `movement_type` ENUM('OPENING', 'PURCHASE', 'SALE', 'CUSTOMER_RETURN', 'SUPPLIER_RETURN', 'DAMAGE', 'ADJUSTMENT') NOT NULL
* `quantity` INT NOT NULL (+ for inward, - for outward)
* `reference_type` ENUM('PURCHASE', 'SALE', 'RETURN', 'MANUAL_ADJUSTMENT') DEFAULT 'MANUAL_ADJUSTMENT'
* `reference_id` INT NULL
* `notes` TEXT
* `movement_date` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP

### 14. `returns` (Customer Returns Header)
* `return_id` INT AUTO_INCREMENT PK
* `sale_id` INT FK → sales(sale_id)
* `customer_id` INT NULL FK → customers(customer_id) ON DELETE SET NULL
* `return_date` DATE NOT NULL
* `return_reason` TEXT
* `total_refund_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00
* `refund_type` ENUM('CASH', 'CREDIT_ADJUSTMENT', 'EXCHANGE') NOT NULL DEFAULT 'CASH'
* `created_by` INT FK → users(user_id)
* `created_at` TIMESTAMP

### 15. `return_items`
* `return_item_id` INT AUTO_INCREMENT PK
* `return_id` INT FK → returns(return_id) ON DELETE CASCADE
* `sale_item_id` INT NULL FK → sale_items(sale_item_id) ON DELETE SET NULL
* `variant_id` INT FK → product_variants(variant_id)
* `quantity` INT NOT NULL (CHECK > 0)
* `unit_price` DECIMAL(10,2) NOT NULL
* `refund_amount` DECIMAL(12,2) NOT NULL
* `condition_status` ENUM('RESTOCKABLE', 'DAMAGED') NOT NULL DEFAULT 'RESTOCKABLE'
* `created_at` TIMESTAMP

---

## Core Relationships

* `categories` 1 → N `products`
* `products` 1 → N `product_variants`
* `suppliers` 1 → N `purchases`
* `purchases` 1 → N `purchase_items` → `product_variants`
* `customers` 1 → N `sales`
* `sales` 1 → N `sale_items` → `product_variants`
* `customers` 1 → N `payments`
* `customers` 1 → N `credit_transactions`
* `product_variants` 1 → N `stock_movements`
* `sales` 1 → N `returns` → `return_items` → `product_variants`
* `users` 1 → N audit records across all transactions
