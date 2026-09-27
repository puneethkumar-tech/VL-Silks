-- =======================================================================
-- VL Silks – Garment Shop Inventory, Sales & Credit Management System
-- Seed Data for Development and Testing
-- =======================================================================

-- 1. USERS
-- Admin credentials: admin@vlsilks.com / Admin@123
-- Staff credentials: staff@vlsilks.com / Staff@123
INSERT INTO users (user_id, name, email, password_hash, role, status) VALUES
(1, 'Venkata Lakshmi (Admin)', 'admin@vlsilks.com', 'scrypt:32768:8:1$djHhwMT74r4MSypZ$690cbec3a7b7ad7d81bb99a722c6cd25cf25261e954068078fbccd24c7c1683f27e47685abc61e9df8883580635ec16a391bc0392071ddf3505dbba8c6af635f', 'ADMIN', 'ACTIVE'),
(2, 'Kiran Kumar (Staff)', 'staff@vlsilks.com', 'scrypt:32768:8:1$zLsWye9AgitCKuXS$1ee78c55a69cdf2155e92db6789fee1f073c2d779de765ce5e452b68bf31da6f8bc3d44437c63de2b605a90ef81ce5c64c713762e583d9ee2b44b021dcc99271', 'STAFF', 'ACTIVE');

-- 2. CATEGORIES
INSERT INTO categories (category_id, category_name, description, status) VALUES
(1, 'Sarees', 'Pure silk, bridal, pattu, banarasi, and designer sarees', 'ACTIVE'),
(2, 'Men\'s Silk & Dhotis', 'Traditional pure silk shirts, angavastrams, and silk dhoti sets', 'ACTIVE'),
(3, 'Shirts & Formals', 'Pure cotton, linen, and formal shirts for men', 'ACTIVE'),
(4, 'T-Shirts & Casuals', 'Premium combed cotton polo and round-neck t-shirts', 'ACTIVE'),
(5, 'Denim & Trousers', 'Classic fit and stretchable denim jeans and trousers', 'ACTIVE'),
(6, 'Kurtis & Ethnic', 'Embroidered, anarkali, straight kurtis, and ethnic dress sets', 'ACTIVE'),
(7, 'Kids Festive Wear', 'Pattu pavadai, kids sherwanis, and festive garments', 'ACTIVE');

-- 3. PRODUCTS
INSERT INTO products (product_id, category_id, product_name, brand, material, description, status) VALUES
(1, 1, 'Kanchipuram Pure Zari Silk Saree', 'VL Silks Heritage', 'Pure Mulberry Silk', 'Handwoven authentic Kanchipuram silk saree with rich gold zari pallu and border', 'ACTIVE'),
(2, 1, 'Banarasi Brocade Silk Saree', 'VL Silks Heritage', 'Banarasi Silk', 'Traditional Banarasi floral jaal brocade saree with contrast blouse piece', 'ACTIVE'),
(3, 2, 'Traditional Men\'s Pure Silk Shirt', 'VL Silks Classic', 'Pure Silk', 'Lustrous cream and golden silk full-sleeve shirt for weddings and festivals', 'ACTIVE'),
(4, 2, 'Silk Dhoti & Angavastram Set (9x5)', 'VL Silks Classic', 'Pure Silk', 'Traditional gold-bordered matching dhoti and shawl set', 'ACTIVE'),
(5, 3, 'Premium Cotton Formal Shirt', 'VL Silks Casuals', '100% Giza Cotton', 'Wrinkle-resistant breathable formal shirt with crisp collar', 'ACTIVE'),
(6, 4, 'Classic Combed Cotton Polo T-Shirt', 'VL Silks Casuals', 'Combed Cotton', 'Pre-shrunk bio-washed casual pique polo t-shirt', 'ACTIVE'),
(7, 5, 'Slim Stretch Denim Jeans', 'VL Silks Denim', 'Cotton Elastane Denim', 'Durable 5-pocket comfortable stretch denim jeans', 'ACTIVE'),
(8, 6, 'Designer Embroidered Anarkali Kurti', 'VL Silks Ethnic', 'Rayon / Georgette', 'Floor-length festive party-wear anarkali kurti with intricate zari work', 'ACTIVE'),
(9, 7, 'Traditional Kids Pattu Pavadai Set', 'VL Silks Kids', 'Art Silk', 'Vibrant traditional lehenga choli set for young girls', 'ACTIVE');

-- 4. PRODUCT VARIANTS
INSERT INTO product_variants (variant_id, product_id, sku, size, color, purchase_price, selling_price, stock_quantity, minimum_stock, barcode, status) VALUES
-- Saree variants (Free Size)
(1, 1, 'SKU-KAN-RED', 'Free Size', 'Crimson Red / Gold Zari', 6500.00, 9999.00, 12, 3, '8901001001', 'ACTIVE'),
(2, 1, 'SKU-KAN-BLU', 'Free Size', 'Royal Blue / Silver Zari', 6500.00, 9999.00, 8, 3, '8901001002', 'ACTIVE'),
(3, 1, 'SKU-KAN-GRN', 'Free Size', 'Peacock Green / Gold Zari', 6800.00, 10499.00, 4, 3, '8901001003', 'ACTIVE'),
(4, 2, 'SKU-BAN-MAR', 'Free Size', 'Deep Maroon', 4500.00, 6999.00, 6, 2, '8901002001', 'ACTIVE'),
(5, 2, 'SKU-BAN-MST', 'Free Size', 'Mustard Yellow', 4500.00, 6999.00, 2, 3, '8901002002', 'ACTIVE'), -- Low stock
-- Silk Shirts
(6, 3, 'SKU-MSK-CRM-40', '40 (M)', 'Rich Cream', 1200.00, 1899.00, 15, 5, '8901003001', 'ACTIVE'),
(7, 3, 'SKU-MSK-CRM-42', '42 (L)', 'Rich Cream', 1200.00, 1899.00, 14, 5, '8901003002', 'ACTIVE'),
(8, 3, 'SKU-MSK-GLD-40', '40 (M)', 'Antique Gold', 1300.00, 1999.00, 10, 4, '8901003003', 'ACTIVE'),
(9, 3, 'SKU-MSK-GLD-42', '42 (L)', 'Antique Gold', 1300.00, 1999.00, 8, 4, '8901003004', 'ACTIVE'),
-- Silk Dhoti Set
(10, 4, 'SKU-DHO-CRM', 'Standard (9x5)', 'Cream / Gold Border', 1400.00, 2250.00, 18, 5, '8901004001', 'ACTIVE'),
-- Cotton Shirts
(11, 5, 'SKU-CSH-WHT-38', '38 (S)', 'Crisp White', 600.00, 999.00, 20, 5, '8901005001', 'ACTIVE'),
(12, 5, 'SKU-CSH-WHT-40', '40 (M)', 'Crisp White', 600.00, 999.00, 25, 5, '8901005002', 'ACTIVE'),
(13, 5, 'SKU-CSH-BLU-40', '40 (M)', 'Sky Blue', 600.00, 999.00, 15, 5, '8901005003', 'ACTIVE'),
-- Polo T-Shirts
(14, 6, 'SKU-POL-BLK-M', 'M', 'Jet Black', 320.00, 599.00, 30, 8, '8901006001', 'ACTIVE'),
(15, 6, 'SKU-POL-BLK-L', 'L', 'Jet Black', 320.00, 599.00, 22, 8, '8901006002', 'ACTIVE'),
(16, 6, 'SKU-POL-MRN-M', 'M', 'Burgundy Maroon', 320.00, 599.00, 18, 8, '8901006003', 'ACTIVE'),
-- Denim Jeans
(17, 7, 'SKU-JNS-BLU-32', '32', 'Dark Indigo Blue', 850.00, 1499.00, 16, 5, '8901007001', 'ACTIVE'),
(18, 7, 'SKU-JNS-BLU-34', '34', 'Dark Indigo Blue', 850.00, 1499.00, 14, 5, '8901007002', 'ACTIVE'),
(19, 7, 'SKU-JNS-BLK-32', '32', 'Washed Black', 850.00, 1499.00, 12, 5, '8901007003', 'ACTIVE'),
-- Kurtis
(20, 8, 'SKU-KUR-MRN-M', 'M', 'Maroon & Gold', 750.00, 1299.00, 10, 4, '8901008001', 'ACTIVE'),
(21, 8, 'SKU-KUR-MRN-L', 'L', 'Maroon & Gold', 750.00, 1299.00, 8, 4, '8901008002', 'ACTIVE'),
(22, 8, 'SKU-KUR-TEL-M', 'M', 'Teal Green', 750.00, 1299.00, 3, 4, '8901008003', 'ACTIVE'), -- Low stock
-- Kids Pattu Pavadai
(23, 9, 'SKU-KID-PNK-24', 'Size 24 (4-5 Yrs)', 'Magenta Pink & Green', 550.00, 950.00, 10, 3, '8901009001', 'ACTIVE'),
(24, 9, 'SKU-KID-YLW-28', 'Size 28 (6-7 Yrs)', 'Golden Yellow & Red', 600.00, 1050.00, 8, 3, '8901009002', 'ACTIVE');

-- 5. SUPPLIERS
INSERT INTO suppliers (supplier_id, supplier_name, contact_person, phone, email, address, gst_number, status) VALUES
(1, 'Sri Kanchi Silk Handloom Weavers Society', 'Murugan Swamy', '9443011223', 'kanchiweavers@gmail.com', '12 Weaver Street, Kanchipuram, Tamil Nadu - 631501', '33AAACK1234F1Z1', 'ACTIVE'),
(2, 'Shree Lakshmi Textiles & Brocades', 'Ramesh Shah', '9825098765', 'laxmitextiles.surat@yahoo.com', '405 Ring Road Textile Market, Surat, Gujarat - 395002', '24AABCS5678D1Z8', 'ACTIVE'),
(3, 'Tirupur Knitwear & Garments Hub', 'Senthil Kumar', '9842054321', 'sales@tirupurgarments.co.in', '78 Avinashi Road, Tirupur, Tamil Nadu - 641603', '33AADCT9012E1Z5', 'ACTIVE'),
(4, 'Bengaluru Silk Emporium', 'Narayana Murthy', '9880012345', 'bengalurusilk@outlook.com', '15 Chickpet Main Road, Bengaluru, Karnataka - 560053', '29AABCB3456G1Z2', 'ACTIVE');

-- 6. PURCHASES
INSERT INTO purchases (purchase_id, supplier_id, invoice_number, purchase_date, subtotal, discount, tax, total, payment_status, notes, created_by) VALUES
(1, 1, 'PUR-KS-2026-001', '2026-09-01', 171800.00, 3800.00, 0.00, 168000.00, 'PAID', 'Festival season bulk Kanchipuram silk purchase', 1),
(2, 3, 'PUR-TK-2026-042', '2026-09-05', 47200.00, 1200.00, 0.00, 46000.00, 'PAID', 'Cotton shirts and polo t-shirts bulk stock', 1),
(3, 2, 'PUR-SL-2026-108', '2026-09-12', 36000.00, 1000.00, 0.00, 35000.00, 'PARTIAL', 'Banarasi sarees and ethnic kurti collection', 1);

-- 7. PURCHASE ITEMS
INSERT INTO purchase_items (purchase_item_id, purchase_id, variant_id, quantity, unit_price, total_price) VALUES
-- Purchase 1 (Kanchi Silks & Dhotis)
(1, 1, 1, 15, 6500.00, 97500.00),
(2, 1, 2, 10, 6500.00, 65000.00),
(3, 1, 10, 20, 1400.00, 28000.00),
-- Purchase 2 (Tirupur Cotton & Polos)
(4, 2, 11, 25, 600.00, 15000.00),
(5, 2, 12, 30, 600.00, 18000.00),
(6, 2, 14, 35, 320.00, 11200.00),
(7, 2, 15, 25, 320.00, 8000.00),
-- Purchase 3 (Banarasi & Kurtis)
(8, 3, 4, 8, 4500.00, 36000.00),
(9, 3, 20, 12, 750.00, 9000.00);

-- 8. CUSTOMERS
INSERT INTO customers (customer_id, customer_name, phone, email, address, credit_limit, status) VALUES
(1, 'Ramesh Kumar', '9845012345', 'ramesh.kumar@gmail.com', '#45 Gandhi Bazar Main Road, Bengaluru', 25000.00, 'ACTIVE'),
(2, 'Priya Sharma', '9845023456', 'priya.sharma@outlook.com', '#12 4th Cross, Malleshwaram, Bengaluru', 30000.00, 'ACTIVE'),
(3, 'Suresh Reddy', '9845034567', 'suresh.reddy@yahoo.com', '#89 8th Main, Jayanagar 4th Block, Bengaluru', 40000.00, 'ACTIVE'),
(4, 'Ananya Patel', '9845045678', 'ananya.p@gmail.com', '#23 Residency Road, Bengaluru', 20000.00, 'ACTIVE'),
(5, 'Rajesh Gupta', '9845056789', 'rajesh.gupta@rediffmail.com', '#102 Commercial Street, Bengaluru', 25000.00, 'ACTIVE');

-- 9. SALES
-- Sale 1: Ramesh Kumar - Partial Payment / Credit Sale (Total: 12,249, Paid: 5,000, Balance: 7,249)
INSERT INTO sales (sale_id, customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, notes, created_by) VALUES
(1, 1, 'INV-2026-0001', '2026-09-10', 12249.00, 0.00, 0.00, 12249.00, 5000.00, 7249.00, 'CREDIT', 'PARTIAL', 'Wedding shopping - advance paid via UPI, remaining on credit', 1);

-- Sale 2: Priya Sharma - Full Cash / UPI Sale (Total: 2,898, Paid: 2,898, Balance: 0)
INSERT INTO sales (sale_id, customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, notes, created_by) VALUES
(2, 2, 'INV-2026-0002', '2026-09-15', 2898.00, 0.00, 0.00, 2898.00, 2898.00, 0.00, 'UPI', 'PAID', 'Full payment received via GooglePay', 2);

-- Sale 3: Suresh Reddy - Pure Credit Sale (Total: 9,999, Paid: 0, Balance: 9,999)
INSERT INTO sales (sale_id, customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, notes, created_by) VALUES
(3, 3, 'INV-2026-0003', '2026-09-18', 9999.00, 0.00, 0.00, 9999.00, 0.00, 9999.00, 'CREDIT', 'CREDIT', 'Purchased Kanchipuram silk saree on monthly udhaar ledger', 1);

-- Sale 4: Walk-in Cash Customer (Total: 1,598, Paid: 1,598, Balance: 0)
INSERT INTO sales (sale_id, customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, notes, created_by) VALUES
(4, NULL, 'INV-2026-0004', '2026-09-22', 1598.00, 0.00, 0.00, 1598.00, 1598.00, 0.00, 'CASH', 'PAID', 'Direct walk-in counter sale', 2);

-- Sale 5: Ramesh Kumar - Additional Credit Sale (Total: 3,798, Paid: 1,000, Balance: 2,798)
INSERT INTO sales (sale_id, customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, notes, created_by) VALUES
(5, 1, 'INV-2026-0005', '2026-09-24', 3798.00, 0.00, 0.00, 3798.00, 1000.00, 2798.00, 'CREDIT', 'PARTIAL', 'Dhoti and silk shirt purchase on existing credit account', 1);

-- 10. SALE ITEMS
INSERT INTO sale_items (sale_item_id, sale_id, variant_id, quantity, unit_price, discount, total_price) VALUES
-- Sale 1: Saree + Dhoti
(1, 1, 1, 1, 9999.00, 0.00, 9999.00),
(2, 1, 10, 1, 2250.00, 0.00, 2250.00),
-- Sale 2: Cotton Shirt + Kurti
(3, 2, 12, 1, 999.00, 0.00, 999.00),
(4, 2, 6, 1, 1899.00, 0.00, 1899.00),
-- Sale 3: Pure Silk Saree
(5, 3, 2, 1, 9999.00, 0.00, 9999.00),
-- Sale 4: Formal Shirt + Polo T-Shirt
(6, 4, 11, 1, 999.00, 0.00, 999.00),
(7, 4, 14, 1, 599.00, 0.00, 599.00),
-- Sale 5: Silk Shirt + Dhoti
(8, 5, 6, 1, 1899.00, 0.00, 1899.00),
(9, 5, 8, 1, 1899.00, 0.00, 1899.00);

-- 11. PAYMENTS (Credit settlements)
-- Ramesh Kumar pays ₹4,000 towards his credit balance on 2026-09-20
INSERT INTO payments (payment_id, customer_id, sale_id, amount, payment_method, payment_date, reference_number, notes, created_by) VALUES
(1, 1, 1, 4000.00, 'UPI', '2026-09-20', 'UPI-REF-99887711', 'Partial settlement of INV-2026-0001', 1),
-- Suresh Reddy pays ₹3,000 towards his credit balance on 2026-09-23
(2, 3, 3, 3000.00, 'CASH', '2026-09-23', 'CASH-REC-0045', 'Part payment for INV-2026-0003', 2);

-- 12. CREDIT TRANSACTIONS (Chronological Ledger)
-- Ramesh Kumar Ledger:
-- 1. Sale INV-2026-0001: Credit incurred = 7,249.00 (Balance: 7,249.00)
-- 2. Payment on Sep 20: Amount = 4,000.00 (Balance: 3,249.00)
-- 3. Sale INV-2026-0005: Credit incurred = 2,798.00 (Balance: 6,047.00)
-- Total outstanding for Ramesh Kumar = ₹6,047.00

-- Suresh Reddy Ledger:
-- 1. Sale INV-2026-0003: Credit incurred = 9,999.00 (Balance: 9,999.00)
-- 2. Payment on Sep 23: Amount = 3,000.00 (Balance: 6,999.00)
-- Total outstanding for Suresh Reddy = ₹6,999.00

-- Total Shop Outstanding Credit to Collect = 6,047 + 6,999 = ₹13,046.00

INSERT INTO credit_transactions (transaction_id, customer_id, sale_id, payment_id, transaction_type, amount, running_balance, transaction_date, notes, created_by) VALUES
(1, 1, 1, NULL, 'CREDIT_SALE', 7249.00, 7249.00, '2026-09-10', 'Credit balance from INV-2026-0001', 1),
(2, 1, NULL, 1, 'PAYMENT', 4000.00, 3249.00, '2026-09-20', 'Credit payment received via UPI', 1),
(3, 3, 3, NULL, 'CREDIT_SALE', 9999.00, 9999.00, '2026-09-18', 'Credit sale INV-2026-0003', 1),
(4, 3, NULL, 2, 'PAYMENT', 3000.00, 6999.00, '2026-09-23', 'Cash payment received against udhaar', 2),
(5, 1, 5, NULL, 'CREDIT_SALE', 2798.00, 6047.00, '2026-09-24', 'Credit balance from INV-2026-0005', 1);

-- 13. STOCK MOVEMENTS
INSERT INTO stock_movements (movement_id, variant_id, movement_type, quantity, reference_type, reference_id, notes, movement_date, created_by) VALUES
-- Opening / Purchases
(1, 1, 'OPENING', 12, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(2, 2, 'OPENING', 8, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(3, 6, 'OPENING', 15, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(4, 10, 'OPENING', 18, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(5, 11, 'OPENING', 20, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(6, 12, 'OPENING', 25, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
(7, 14, 'OPENING', 30, 'MANUAL_ADJUSTMENT', NULL, 'Initial stock count', '2026-09-01 09:00:00', 1),
-- Sales Outward
(8, 1, 'SALE', -1, 'SALE', 1, 'Sold on INV-2026-0001', '2026-09-10 11:30:00', 1),
(9, 10, 'SALE', -1, 'SALE', 1, 'Sold on INV-2026-0001', '2026-09-10 11:30:00', 1),
(10, 12, 'SALE', -1, 'SALE', 2, 'Sold on INV-2026-0002', '2026-09-15 16:45:00', 2),
(11, 6, 'SALE', -1, 'SALE', 2, 'Sold on INV-2026-0002', '2026-09-15 16:45:00', 2),
(12, 2, 'SALE', -1, 'SALE', 3, 'Sold on INV-2026-0003', '2026-09-18 14:15:00', 1),
(13, 11, 'SALE', -1, 'SALE', 4, 'Sold on INV-2026-0004', '2026-09-22 18:00:00', 2),
(14, 14, 'SALE', -1, 'SALE', 4, 'Sold on INV-2026-0004', '2026-09-22 18:00:00', 2);

-- 14. RETURNS (Sample return for demonstration)
INSERT INTO returns (return_id, sale_id, customer_id, return_date, return_reason, total_refund_amount, refund_type, created_by) VALUES
(1, 4, NULL, '2026-09-23', 'Size exchange/return - customer requested different color', 599.00, 'CASH', 2);

-- 15. RETURN ITEMS
INSERT INTO return_items (return_item_id, return_id, sale_item_id, variant_id, quantity, unit_price, refund_amount, condition_status) VALUES
(1, 1, 7, 14, 1, 599.00, 599.00, 'RESTOCKABLE');

-- Restock stock movement for the return
INSERT INTO stock_movements (movement_id, variant_id, movement_type, quantity, reference_type, reference_id, notes, movement_date, created_by) VALUES
(15, 14, 'CUSTOMER_RETURN', 1, 'RETURN', 1, 'Customer returned polo t-shirt in sellable condition', '2026-09-23 10:30:00', 2);
