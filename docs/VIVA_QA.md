# Comprehensive Viva Voce Preparation Guide
## VL Silks - Garment Shop Inventory, Sales & Credit Management System
**Total Questions:** 60 Questions across 10 Technical Sections
---
## SECTION 1: Project Overview & Problem Domain
### Q1. What is VL Silks and why was it developed?
**Answer:** VL Silks is a specialized, web-based Garment Shop Inventory, Sales, and Credit Management System. It was designed to replace manual, error-prone paper ledgers, stock registers, and physical Udhaar notebooks in traditional Indian silk garment retail shops. It provides centralized multi-variant inventory control, rapid POS checkout with multiple payment modes, an authoritative running Udhaar credit ledger, returns/exchanges management, and business intelligence reporting.
### Q2. What are the key business challenges unique to a garment shop?
**Answer:**
1. **Multi-Variant Products:** Each garment design comes in multiple sizes and color combinations, each with distinct SKUs, costs, prices, and stock counts.
2. **Frequent Credit (Udhaar) Sales:** Customers often buy on credit and make partial payments over time, leading to balance disputes in manual systems.
3. **Complex Returns & Exchanges:** Customers frequently swap garments for different sizes/colors or return items, requiring condition checks (restockable vs. damaged) and price difference adjustments.
4. **Stock Discrepancies:** Fast festival sales lead to stock mismatches unless every inventory change is atomically recorded in an audit trail.
### Q3. What technology stack does VL Silks use?
**Answer:**
- **Backend Framework:** Python 3.12+ with Flask.
- **Database:** MySQL 8.x (InnoDB engine with utf8mb4 encoding).
- **Frontend / UI:** HTML5, Vanilla CSS3, Bootstrap 5, Jinja2 template engine, and Vanilla JavaScript.
- **Charts / Visualizations:** Chart.js.
- **PDF Engine:** ReportLab for server-side generation of A4 customer credit statements.
- **Testing:** Pytest (390 tests collected: 388 passed, 2 skipped across 16 test modules).
### Q4. What are the main modules of the system?
**Answer:**
1. Authentication & Role-Based Access Control (Admin vs. Staff)
2. Product & Multi-Variant Catalog Management
3. Category & Supplier Management
4. Inward Purchase Procurement
5. Real-Time Inventory & Stock Movement Audit
6. Point of Sale (POS) Billing & Invoicing
7. Customer Profile & Udhaar Credit Ledger
8. PDF Credit Statement Generator
9. Returns & Garment Exchanges
10. Dashboard Analytics & Business Reports (Sales, Purchases, Valuation, Aging, Profit)
---
## SECTION 2: System Architecture & Design
### Q5. What architectural design pattern does VL Silks follow?
**Answer:** VL Silks follows a classic **Three-Tier Architecture** adhering to the **Model-Template-Service** structure:
1. **Presentation Tier:** Browser interface using HTML/CSS/Bootstrap/JS and Jinja2 server-rendered templates.
2. **Application Tier:** Flask Application Factory (`create_app`), modular Blueprints for routing, and a dedicated Service Layer encapsulating all business logic.
3. **Data Tier:** MySQL 8.x relational database managing 15 normalized tables.
### Q6. Why is the business logic separated into a Service Layer?
**Answer:** Isolating business logic in `backend/services/` keeps Flask route handlers ("controllers") thin and focused only on HTTP request/response parsing. The service layer contains all SQL queries, data validations, Decimal calculations, and transactional boundaries. This makes the code modular, reusable, easily testable via automated unit tests, and maintainable.
### Q7. What is the Flask Application Factory pattern and why is it used?
**Answer:** The Application Factory pattern creates the Flask app instance inside a function (`create_app(config_name)`) rather than as a global object. This allows instantiating the app with different configurations - such as `TestingConfig` with a separate test database or `DevelopmentConfig` - without modifying source code.
---
## SECTION 3: Database Design, Schema & Normalization
### Q8. How many tables are in the VL Silks database? Name them.
**Answer:** The database contains **15 normalized tables**:
1. `users`
2. `categories`
3. `products`
4. `product_variants`
5. `suppliers`
6. `purchases`
7. `purchase_items`
8. `customers`
9. `sales`
10. `sale_items`
11. `payments`
12. `credit_transactions`
13. `stock_movements`
14. `returns`
15. `return_items`
### Q9. What normal form does the database satisfy? Explain with examples.
**Answer:** The database satisfies **Third Normal Form (3NF)**:
- **1NF:** All attributes are atomic. Line items are separated into child tables (`sale_items`, `purchase_items`, `return_items`) rather than comma-delimited strings.
- **2NF:** Every table uses a single-column primary key (`AUTO_INCREMENT INT`), so partial dependencies on composite keys are impossible.
- **3NF:** Transitive dependencies are eliminated by separating Categories from Products, Base Products from Variants, and Customer profiles from Sales invoices. Point-in-time financial snapshots (e.g. invoice totals) are retained for legal auditability.
### Q10. Why is the catalog split into `products` and `product_variants`?
**Answer:** A base product (e.g., *Pure Kanjivaram Silk Saree*) shares common attributes such as brand, material, description, and category. However, individual variations have different sizes, colors, SKUs, barcodes, purchase costs, selling prices, and stock counts. Splitting into `products` (1) to `product_variants` (N) eliminates data redundancy and prevents update anomalies.
### Q11. How is negative stock prevented at the database level?
**Answer:** The `product_variants` table includes an explicit MySQL `CHECK` constraint: `CHECK (stock_quantity >= 0)`. Any SQL statement that would cause stock to drop below zero is immediately aborted by the database engine with a constraint violation.
---
## SECTION 4: Point of Sale (POS) & Billing
### Q12. What payment methods does the POS system support?
**Answer:** The system supports 5 payment modes: `CASH`, `UPI`, `CARD`, `CREDIT` (Udhaar), and `SPLIT` (part cash/digital and part credit).
### Q13. How does the POS handle Credit (Udhaar) sales?
**Answer:** When an invoice is billed with a credit balance (`balance_amount > 0`):
1. A registered customer must be selected (walk-in credit is rejected).
2. The system checks if `current_balance + new_balance <= credit_limit`. If exceeded, the checkout is rejected.
3. Upon checkout, the sale is recorded, stock is deducted, and a debit entry of type `CREDIT_SALE` is automatically appended to `credit_transactions`.
### Q14. How are invoice numbers generated?
**Answer:** Invoices use the standard format `SALE-YYYY-NNNN` (e.g., `SALE-2026-0001`). The system queries the maximum sequential number for the current year within an atomic transaction to ensure uniqueness.
---
## SECTION 5: Credit / Udhaar Management & PDF Generation
### Q15. How does the Udhaar ledger work?
**Answer:** The system maintains an append-only transaction ledger in `credit_transactions`. 
- `CREDIT_SALE` adds to the customer's outstanding balance.
- `PAYMENT` (settlement payment) subtracts from the balance.
- `RETURN_REFUND` (credit adjustment for returned items) subtracts from the balance.
The customer's outstanding balance is computed directly by summing ledger entries, ensuring an immutable audit trail.
### Q16. How is overpayment prevented in credit settlement?
**Answer:** Before inserting a payment into `payments` and `credit_transactions`, `credit_service.py` computes the customer's exact current balance. If `payment_amount > current_balance`, the system rejects the transaction with an `OverpaymentError`.
### Q17. How are PDF credit statements generated?
**Answer:** PDF statements are generated server-side using the Python **ReportLab** library in `backend/services/pdf_service.py`. The service fetches the customer profile and ledger history, builds a multi-page A4 document with the VL Silks gold/maroon brand palette, customer metadata, itemized ledger table, and balance summary boxes, and streams the PDF bytes to the client. PDF generation is strictly read-only with zero database side-effects.
---
## SECTION 6: Inventory Movements & Audit Trail
### Q18. What are the 5 stock movement types and when are they triggered?
**Answer:**
1. `PURCHASE` (+ qty): Inward supplier invoice confirmed.
2. `SALE` (- qty): Customer invoice processed at POS.
3. `CUSTOMER_RETURN` (+ qty): Restockable garment returned by customer.
4. `DAMAGE` (0 / - qty): Garment returned damaged or written off; stock is not put on shelves.
5. `ADJUSTMENT` (+ / - qty): Manual inventory count reconciliation by Admin.
### Q19. Why not just update the `stock_quantity` column without `stock_movements`?
**Answer:** Updating only `stock_quantity` overwrites the number without preserving history. If stock goes missing or discrepancies occur, there would be no way to know who changed the stock, when, or why. `stock_movements` provides a complete, non-repudiable financial and operational audit trail.
---
## SECTION 7: Returns & Exchanges
### Q20. What is the difference between RESTOCKABLE and DAMAGED returns?
**Answer:**
- `RESTOCKABLE`: The garment is in pristine condition. `stock_quantity` is incremented and a `CUSTOMER_RETURN` movement is logged.
- `DAMAGED`: The garment has tears or stains. `stock_quantity` is NOT incremented (preventing defective resale), but a `DAMAGE` audit record is logged.
### Q21. How is over-return prevented?
**Answer:** The return service queries `SUM(quantity)` from `return_items` for the specific `sale_item_id`. It enforces that `current_return_qty <= (original_sold_qty - already_returned_qty)`. A customer cannot return more items than were originally bought.
### Q22. How does a garment exchange work?
**Answer:** In a single atomic transaction:
1. The returned item is processed (restocked or marked damaged).
2. The replacement variant is checked for stock and deducted.
3. The price difference (`replacement_price - returned_price`) is calculated:
   - If positive: Customer pays difference at counter (Cash/UPI) or adds to Udhaar.
   - If negative: Difference is refunded via Cash or Udhaar credit adjustment.
---
## SECTION 8: Security & Concurrency
### Q23. How does the system prevent SQL Injection?
**Answer:** Every database interaction throughout all services uses **parameterized queries** with `mysql-connector-python` `%s` placeholders. User inputs are passed as separate parameter tuples/dictionaries to the MySQL driver and never concatenated into SQL strings.
### Q24. How are passwords secured?
**Answer:** Passwords are never stored in plaintext. They are hashed using `werkzeug.security.generate_password_hash` with the `scrypt` algorithm, which is salted, memory-hard, and computationally resistant to brute-force attacks.
### Q25. How is role-based authorization enforced?
**Answer:** Custom Python decorators `@login_required` and `@admin_required` wrap route handlers. 
- `@login_required` checks for an active session user ID.
- `@admin_required` verifies `session['user_role'] == 'ADMIN'`. If a Staff user attempts an Admin route, the system responds with `403 Forbidden`.
### Q26. Why is Python `decimal.Decimal` used instead of `float` for money?
**Answer:** Binary floating-point numbers (`float`) cannot accurately represent all decimal fractions due to IEEE 754 representation limits (e.g., `0.1 + 0.2 = 0.30000000000000004`). In a retail system with discounts, taxes, and ledgers, floating-point drift creates cumulative rounding errors. Python's `decimal.Decimal` provides exact base-10 arithmetic.
---
## SECTION 9: Testing & Quality Assurance
### Q27. How was the system tested?
**Answer:** The system was verified using automated unit, integration, and security tests written with `pytest`. The test suite contains **390 tests collected: 388 passed, 2 skipped** across **16 test modules** covering business services, routes, validations, edge cases, and role restrictions. Additionally, 13 Playwright end-to-end smoke tests were run against an isolated test database (`vl_silks_test_db`) covering Desktop/Mobile viewports, POS checkout, credit PDF, returns, all 5 report types, and RBAC enforcement.
### Q28. What edge cases are covered in the test suite?
**Answer:**
- Attempting to sell items with insufficient stock (rejection).
- Over-returning items beyond invoice count (rejection).
- Overpaying credit balance (rejection).
- Bypassing authentication or performing admin actions as staff (401 / 403).
- Rollback verification on mid-transaction failures.
- Non-negative stock constraint enforcement.
---
## SECTION 10: Summary & Viva Quick Fire
### Q29. What happens if the database crashes during a POS checkout?
**Answer:** Because all writes (sale, items, stock deduction, movement log, payment, credit transaction) are executed inside an explicit `conn.begin()` block, MySQL's InnoDB transaction engine rolls back all uncommitted changes upon failure. No orphan or partial records are saved.
### Q30. Why is MySQL InnoDB used instead of MyISAM?
**Answer:** InnoDB supports ACID transactions (`COMMIT`/`ROLLBACK`), Foreign Key constraints with referential integrity (`RESTRICT`/`CASCADE`), row-level locking for concurrency, and crash recovery via write-ahead logging (`redo log`). MyISAM lacks transaction and foreign key support.
