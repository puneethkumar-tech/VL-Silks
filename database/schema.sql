-- =======================================================================
-- VL Silks – Garment Shop Inventory, Sales & Credit Management System
-- Database Schema (MySQL 8.x)
-- =======================================================================

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS return_items;
DROP TABLE IF EXISTS returns;
DROP TABLE IF EXISTS stock_movements;
DROP TABLE IF EXISTS credit_transactions;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS sale_items;
DROP TABLE IF EXISTS sales;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS purchase_items;
DROP TABLE IF EXISTS purchases;
DROP TABLE IF EXISTS suppliers;
DROP TABLE IF EXISTS product_variants;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------
-- 1. USERS
-- -----------------------------------------------------------------------
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('ADMIN', 'STAFF') NOT NULL DEFAULT 'STAFF',
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 2. CATEGORIES
-- -----------------------------------------------------------------------
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_categories_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 3. PRODUCTS (Base Garment)
-- -----------------------------------------------------------------------
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    product_name VARCHAR(150) NOT NULL,
    brand VARCHAR(100) DEFAULT 'VL Silks',
    material VARCHAR(100),
    description TEXT,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) 
        REFERENCES categories (category_id) ON DELETE RESTRICT,
    INDEX idx_products_category (category_id),
    INDEX idx_products_name (product_name),
    INDEX idx_products_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 4. PRODUCT VARIANTS (Size, Color, Stock, SKU)
-- -----------------------------------------------------------------------
CREATE TABLE product_variants (
    variant_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    sku VARCHAR(50) NOT NULL UNIQUE,
    size VARCHAR(30) NOT NULL,
    color VARCHAR(50) NOT NULL,
    purchase_price DECIMAL(10, 2) NOT NULL CHECK (purchase_price >= 0),
    selling_price DECIMAL(10, 2) NOT NULL CHECK (selling_price >= 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    minimum_stock INT NOT NULL DEFAULT 5 CHECK (minimum_stock >= 0),
    barcode VARCHAR(100) UNIQUE,
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_variants_product FOREIGN KEY (product_id) 
        REFERENCES products (product_id) ON DELETE RESTRICT,
    INDEX idx_variants_product (product_id),
    INDEX idx_variants_sku (sku),
    INDEX idx_variants_stock (stock_quantity),
    INDEX idx_variants_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 5. SUPPLIERS
-- -----------------------------------------------------------------------
CREATE TABLE suppliers (
    supplier_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    address TEXT,
    gst_number VARCHAR(30),
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_suppliers_phone (phone),
    INDEX idx_suppliers_name (supplier_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 6. PURCHASES (Inward Supplier Invoices)
-- -----------------------------------------------------------------------
CREATE TABLE purchases (
    purchase_id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_id INT NOT NULL,
    invoice_number VARCHAR(50) NOT NULL,
    purchase_date DATE NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (subtotal >= 0),
    discount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (discount >= 0),
    tax DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (tax >= 0),
    total DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (total >= 0),
    payment_status ENUM('PAID', 'PARTIAL', 'PENDING') NOT NULL DEFAULT 'PAID',
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_purchases_supplier FOREIGN KEY (supplier_id) 
        REFERENCES suppliers (supplier_id) ON DELETE RESTRICT,
    CONSTRAINT fk_purchases_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_purchases_supplier (supplier_id),
    INDEX idx_purchases_date (purchase_date),
    INDEX idx_purchases_invoice (invoice_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 7. PURCHASE ITEMS
-- -----------------------------------------------------------------------
CREATE TABLE purchase_items (
    purchase_item_id INT AUTO_INCREMENT PRIMARY KEY,
    purchase_id INT NOT NULL,
    variant_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_price DECIMAL(12, 2) NOT NULL CHECK (total_price >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_purchase_items_purchase FOREIGN KEY (purchase_id) 
        REFERENCES purchases (purchase_id) ON DELETE CASCADE,
    CONSTRAINT fk_purchase_items_variant FOREIGN KEY (variant_id) 
        REFERENCES product_variants (variant_id) ON DELETE RESTRICT,
    INDEX idx_purchase_items_purchase (purchase_id),
    INDEX idx_purchase_items_variant (variant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 8. CUSTOMERS
-- -----------------------------------------------------------------------
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(150) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(100),
    address TEXT,
    credit_limit DECIMAL(12, 2) DEFAULT 25000.00 CHECK (credit_limit >= 0),
    status ENUM('ACTIVE', 'INACTIVE') NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customers_phone (phone),
    INDEX idx_customers_name (customer_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 9. SALES (Billing Invoices)
-- -----------------------------------------------------------------------
CREATE TABLE sales (
    sale_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NULL,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    sale_date DATE NOT NULL,
    subtotal DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (subtotal >= 0),
    discount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (discount >= 0),
    tax DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (tax >= 0),
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_amount >= 0),
    paid_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (paid_amount >= 0),
    balance_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (balance_amount >= 0),
    payment_method ENUM('CASH', 'UPI', 'CARD', 'CREDIT', 'SPLIT') NOT NULL DEFAULT 'CASH',
    payment_status ENUM('PAID', 'PARTIAL', 'CREDIT') NOT NULL DEFAULT 'PAID',
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_sales_customer FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) ON DELETE SET NULL,
    CONSTRAINT fk_sales_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_sales_customer (customer_id),
    INDEX idx_sales_date (sale_date),
    INDEX idx_sales_invoice (invoice_number),
    INDEX idx_sales_status (payment_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 10. SALE ITEMS
-- -----------------------------------------------------------------------
CREATE TABLE sale_items (
    sale_item_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    variant_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    discount DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (discount >= 0),
    total_price DECIMAL(12, 2) NOT NULL CHECK (total_price >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sale_items_sale FOREIGN KEY (sale_id) 
        REFERENCES sales (sale_id) ON DELETE CASCADE,
    CONSTRAINT fk_sale_items_variant FOREIGN KEY (variant_id) 
        REFERENCES product_variants (variant_id) ON DELETE RESTRICT,
    INDEX idx_sale_items_sale (sale_id),
    INDEX idx_sale_items_variant (variant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 11. PAYMENTS (Credit settlements & collections)
-- -----------------------------------------------------------------------
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    sale_id INT NULL,
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    payment_method ENUM('CASH', 'UPI', 'CARD', 'BANK_TRANSFER') NOT NULL DEFAULT 'CASH',
    payment_date DATE NOT NULL,
    reference_number VARCHAR(100),
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_payments_sale FOREIGN KEY (sale_id) 
        REFERENCES sales (sale_id) ON DELETE SET NULL,
    CONSTRAINT fk_payments_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_payments_customer (customer_id),
    INDEX idx_payments_date (payment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 12. CREDIT TRANSACTIONS (Udhaar Ledger)
-- -----------------------------------------------------------------------
CREATE TABLE credit_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    sale_id INT NULL,
    payment_id INT NULL,
    transaction_type ENUM('CREDIT_SALE', 'PAYMENT', 'RETURN_REFUND', 'ADJUSTMENT') NOT NULL,
    amount DECIMAL(12, 2) NOT NULL CHECK (amount > 0),
    running_balance DECIMAL(12, 2) NULL,
    transaction_date DATE NOT NULL,
    notes TEXT,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_credit_tx_customer FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) ON DELETE RESTRICT,
    CONSTRAINT fk_credit_tx_sale FOREIGN KEY (sale_id) 
        REFERENCES sales (sale_id) ON DELETE SET NULL,
    CONSTRAINT fk_credit_tx_payment FOREIGN KEY (payment_id) 
        REFERENCES payments (payment_id) ON DELETE SET NULL,
    CONSTRAINT fk_credit_tx_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_credit_tx_customer (customer_id),
    INDEX idx_credit_tx_date (transaction_date),
    INDEX idx_credit_tx_type (transaction_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 13. STOCK MOVEMENTS (Audit trail of every inventory change)
-- -----------------------------------------------------------------------
CREATE TABLE stock_movements (
    movement_id INT AUTO_INCREMENT PRIMARY KEY,
    variant_id INT NOT NULL,
    movement_type ENUM('OPENING', 'PURCHASE', 'SALE', 'CUSTOMER_RETURN', 'SUPPLIER_RETURN', 'DAMAGE', 'ADJUSTMENT') NOT NULL,
    quantity INT NOT NULL, -- Positive for stock increase, negative for stock reduction
    reference_type ENUM('PURCHASE', 'SALE', 'RETURN', 'MANUAL_ADJUSTMENT') DEFAULT 'MANUAL_ADJUSTMENT',
    reference_id INT NULL,
    notes TEXT,
    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_stock_movements_variant FOREIGN KEY (variant_id) 
        REFERENCES product_variants (variant_id) ON DELETE RESTRICT,
    CONSTRAINT fk_stock_movements_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_movements_variant (variant_id),
    INDEX idx_movements_type (movement_type),
    INDEX idx_movements_date (movement_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 14. RETURNS (Customer garment returns)
-- -----------------------------------------------------------------------
CREATE TABLE returns (
    return_id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    customer_id INT NULL,
    return_date DATE NOT NULL,
    return_reason TEXT,
    total_refund_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (total_refund_amount >= 0),
    refund_type ENUM('CASH', 'CREDIT_ADJUSTMENT', 'EXCHANGE') NOT NULL DEFAULT 'CASH',
    created_by INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_returns_sale FOREIGN KEY (sale_id) 
        REFERENCES sales (sale_id) ON DELETE RESTRICT,
    CONSTRAINT fk_returns_customer FOREIGN KEY (customer_id) 
        REFERENCES customers (customer_id) ON DELETE SET NULL,
    CONSTRAINT fk_returns_user FOREIGN KEY (created_by) 
        REFERENCES users (user_id) ON DELETE RESTRICT,
    INDEX idx_returns_sale (sale_id),
    INDEX idx_returns_customer (customer_id),
    INDEX idx_returns_date (return_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------------------------
-- 15. RETURN ITEMS
-- -----------------------------------------------------------------------
CREATE TABLE return_items (
    return_item_id INT AUTO_INCREMENT PRIMARY KEY,
    return_id INT NOT NULL,
    sale_item_id INT NULL,
    variant_id INT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    refund_amount DECIMAL(12, 2) NOT NULL CHECK (refund_amount >= 0),
    condition_status ENUM('RESTOCKABLE', 'DAMAGED') NOT NULL DEFAULT 'RESTOCKABLE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_return_items_return FOREIGN KEY (return_id) 
        REFERENCES returns (return_id) ON DELETE CASCADE,
    CONSTRAINT fk_return_items_sale_item FOREIGN KEY (sale_item_id) 
        REFERENCES sale_items (sale_item_id) ON DELETE SET NULL,
    CONSTRAINT fk_return_items_variant FOREIGN KEY (variant_id) 
        REFERENCES product_variants (variant_id) ON DELETE RESTRICT,
    INDEX idx_return_items_return (return_id),
    INDEX idx_return_items_variant (variant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
