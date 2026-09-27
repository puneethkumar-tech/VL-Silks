# Security & Data Integrity
## VL Silks - Security Architecture and Data Integrity Protocols
---
## 1. Authentication & Password Security
- **Hashing Algorithm:** Uses Python's `werkzeug.security` implementation of `scrypt` (memory-hard, resistant to GPU/ASIC brute-force attacks).
- **Zero Plaintext Storage:** Passwords are never logged, echoed, or stored in plaintext.
- **Session Protection:** Flask secure server-side signed sessions using a cryptographically secure `SECRET_KEY`.
- **Active Account Check:** Even with a valid session cookie, deactivated accounts (`status != 'ACTIVE'`) are rejected at the decorator level.
---
## 2. Role-Based Access Control (RBAC)
Two distinct user tiers are strictly enforced:
| Operational Capability | Staff Role | Admin Role | Enforced By |
|---|---|---|---|
| View Dashboard & Inventory | Yes | Yes | `@login_required` |
| Process POS Sales & Invoices | Yes | Yes | `@login_required` |
| Record Credit Payments | Yes | Yes | `@login_required` |
| Process Returns & Exchanges | Yes | Yes | `@login_required` |
| Download PDF Statements | Yes | Yes | `@login_required` |
| Create / Edit Products & Variants | No (403) | Yes | `@admin_required` |
| Enter Inward Supplier Purchases | No (403) | Yes | `@admin_required` |
| Perform Manual Stock Adjustments | No (403) | Yes | `@admin_required` |
| Register Suppliers / Customers | No (403) | Yes | `@admin_required` |
| View Financial & Profit Reports | No (403) | Yes | `@admin_required` |
---
## 3. SQL Injection Prevention
- **100% Parameterized Queries:** Every database query in the entire application utilizes `mysql-connector-python` tuple/dictionary parameter placeholders (`%s`).
- **No String Formatting in SQL:** No `f"SELECT ... {user_input}"` or string concatenation exists anywhere in the codebase.
- **Strict Data Type Casting:** IDs, numbers, and dates are explicitly cast and validated in service layers before query execution.
---
## 4. Financial Precision & Integrity
- **Decimal Arithmetic:** All monetary amounts (`unit_price`, `subtotal`, `discount`, `tax`, `total_amount`, `paid_amount`, `balance_amount`, `running_balance`, `refund_amount`) are handled using `decimal.Decimal` quantized to 2 decimal places (`Decimal('0.01')`).
- **Zero Floating-Point Drift:** Floating-point math (`float`) is strictly prohibited in monetary calculations to prevent IEEE 754 precision leakage.
- **Overpayment Prevention:** The system validates that credit payments cannot exceed the customer's outstanding balance.
---
## 5. ACID Transactional Safety
- **Multi-Table Integrity:** Operations that modify multiple tables (e.g., checkout modifying sales, sale items, variant stock, movements, payments, and credit ledger) are wrapped in `conn.begin()` ... `conn.commit()`.
- **Automated Rollback:** If any step fails (e.g., constraint violation, insufficient stock), the entire transaction is rolled back (`conn.rollback()`), guaranteeing zero partial state corruption.
- **Database CHECK Constraint:** MySQL enforces `CHECK (stock_quantity >= 0)` on `product_variants`, preventing negative stock even in concurrent edge cases.
