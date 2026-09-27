# VL Silks

# Product Requirements Document

## 1. Product Name

VL Silks – Garment Shop Inventory, Sales & Credit Management System

---

# 2. Product Vision

Build a simple, reliable web application that helps a small garment shop manage daily business operations digitally.

The application should replace manual registers for:

* Products
* Stock
* Purchases
* Sales
* Customers
* Credit/Udhaar
* Payments
* Reports

The application must remain simple enough for a college DBMS project while following realistic business workflows.

---

# 3. Target Users

## Admin

The shop owner or administrator.

Permissions:

* Full dashboard
* Manage products
* Manage categories
* Manage suppliers
* Manage customers
* Manage purchases
* Manage sales
* Manage inventory
* Manage credit
* Record payments
* View reports
* Export PDFs
* Manage staff users

## Staff

Shop employee.

Permissions:

* View products
* Create sales
* Manage customers
* Record customer payments
* View inventory
* View relevant reports

Staff should not be allowed to perform sensitive administrative operations unless explicitly permitted.

---

# 4. Authentication

The application must have:

* Login
* Logout
* Session management
* Password hashing
* Role-based access

Login fields:

* Username/email
* Password

Future enhancement:

* Password reset
* Email verification

These are not required for the first version.

---

# 5. Dashboard

The dashboard is the main landing page after login.

## Required cards

### Total Products

Number of active products.

### Total Stock

Total quantity of available inventory.

### Today's Sales

Total sales amount for the current date.

### Today's Purchases

Total purchases for the current date.

### Credit to Collect

Total outstanding credit from all customers.

Formula:

Outstanding Credit =
Total Credit Sales - Credit Payments - Relevant Adjustments

### Customers With Credit

Number of customers whose outstanding balance is greater than zero.

### Low Stock

Number of products below their configured minimum stock level.

---

# 6. Product & Variant Management

The catalog is structured hierarchically into Base Products and Stock-Keeping Variants:

Admin can:
* Add / Edit / Deactivate base product
* Add / Edit / Deactivate product variants (SKUs)
* Search and filter by category, brand, SKU, and barcode
* View product details and variant breakdown

### Product-level Attributes:
* Product ID
* Product Name
* Category
* Brand
* Material
* Description
* Status (`ACTIVE`, `INACTIVE`)
* *Image (Future enhancement — not in current system scope)*

### Variant-level Attributes (SKU):
* SKU (Stock Keeping Unit — unique identifier)
* Barcode (optional unique retail barcode)
* Size (e.g., `S`, `M`, `L`, `XL`, `Free Size`, `9x5`)
* Color (e.g., `Crimson Red / Gold Zari`, `Royal Blue`)
* Purchase Price (Cost)
* Selling Price (Retail MRP)
* Minimum Stock Level (Low-stock threshold)
* Status (`ACTIVE`, `INACTIVE`)

Example:
Base Product: *Kanchipuram Pure Zari Silk Saree* (Brand: VL Silks Heritage, Material: Pure Mulberry Silk)
Variants:
- SKU-KAN-RED / Free Size / Crimson Red / Cost ₹6,500 / Price ₹9,999 / Min Stock 3
- SKU-KAN-BLU / Free Size / Royal Blue / Cost ₹6,500 / Price ₹9,999 / Min Stock 3

---

# 7. Category Management

Admin can:

* Create category
* Edit category
* Deactivate category
* View products under category

Example categories:

* Sarees
* Men's Silk & Dhotis
* Shirts & Formals
* T-Shirts & Casuals
* Denim & Trousers
* Kurtis & Ethnic
* Kids Festive Wear

---

# 8. Inventory Management

Inventory tracks stock movement in real time via an immutable audit trail (`stock_movements`).

Stock changes occur from:

* Inward purchase (`PURCHASE` — +Qty)
* Outward POS sale (`SALE` — -Qty)
* Customer return (`CUSTOMER_RETURN` — +Qty for RESTOCKABLE)
* Damaged write-off (`DAMAGE` — recorded for damaged goods)
* Manual stock correction (`ADJUSTMENT` — +Qty or -Qty)
* *Supplier return (Future scope — not part of current operational workflow)*

Every inventory change creates a timestamped stock movement audit log with before/after quantities.

---

# 9. Low Stock

Every product can have a minimum stock level.

Example:

Current stock = 3

Minimum stock = 5

The product is considered low stock.

Dashboard should display it.

---

# 10. Supplier Management

Supplier fields:

* Supplier ID
* Supplier name
* Phone
* Email
* Address
* GST number

Features:

* Add supplier
* Edit supplier
* View supplier
* View purchase history

---

# 11. Purchase Management

A purchase contains:

* Purchase ID
* Supplier
* Purchase date
* Invoice number
* Items
* Quantity
* Purchase price
* Discount
* Tax if required
* Total
* Payment status

Each purchase contains multiple purchase items.

After a purchase is confirmed:

Inventory should increase.

---

# 12. Sales Management

A sale contains:

* Sale ID
* Invoice number
* Customer
* Date
* Items
* Quantity
* Selling price
* Discount
* Total
* Payment method
* Payment status

Payment methods:

* Cash
* UPI
* Card
* Credit (Udhaar)
* Split (Multi-mode combination)

After a sale is confirmed:

Inventory should decrease.

---

# 13. Customer Management

Customer fields:

* Customer ID
* Name
* Phone
* Address
* Email

Customer profile must display:

* Personal information
* Purchase history
* Payment history
* Credit balance
* Complete credit transaction history

---

# 14. Credit / Udhaar Management

Credit is one of the core features of the application.

Example:

Sale = ₹5,000

Paid = ₹2,000

Outstanding = ₹3,000

The outstanding amount must be associated with the customer.

---

# 15. Credit History

Every customer should have a complete chronological credit history.

Example:

| Date   | Type        | Reference | Credit |   Paid | Balance |
| ------ | ----------- | --------- | -----: | -----: | ------: |
| 10 Sep | Credit Sale | INV001    | ₹3,000 | ₹1,000 |  ₹2,000 |
| 15 Sep | Credit Sale | INV008    | ₹2,500 |     ₹0 |  ₹4,500 |
| 20 Sep | Payment     | PAY003    |     ₹0 | ₹1,500 |  ₹3,000 |

The customer should be able to see their complete history from the available transaction records.

---

# 16. Credit Payment

Admin/staff can record a payment against a customer's outstanding credit.

Fields:

* Customer
* Amount
* Payment method
* Payment date
* Reference number
* Notes

After recording payment:

Outstanding balance must update immediately.

---

# 17. Credit PDF Statement

Each customer must have an:

**Export Credit History PDF**

button.

The PDF must contain:

* VL Silks logo
* VL Silks name
* Tagline
* Customer name
* Customer phone
* Statement period
* Transaction history
* Total credit
* Total paid
* Outstanding balance
* Generated date
* Footer

PDF generation technology:

ReportLab.

---

# 18. Returns

The system should support basic customer returns.

When an item is returned:

* Return is recorded
* Inventory is updated
* Relevant sale information is preserved
* Payment/credit adjustment is recorded when applicable

---

# 19. Exchanges

Basic garment exchanges can be supported.

Example:

Customer returns:

Black T-Shirt / M

Customer receives:

Black T-Shirt / L

Inventory must reflect both changes.

---

# 20. Reports

Required reports:

### Sales

* Daily sales
* Monthly sales
* Product-wise sales
* Customer-wise sales

### Purchases

* Daily purchases
* Monthly purchases
* Supplier-wise purchases

### Inventory

* Current stock
* Low stock
* Out of stock
* Stock movement

### Credit

* Total credit outstanding
* Customer-wise outstanding
* Credit history
* Payment history

### Profit

Basic profit:

Selling Price - Purchase Price

---

# 21. PDF Documents

The system may generate:

1. Sales invoice
2. Purchase bill
3. Customer credit statement
4. Reports when useful

All PDFs should use VL Silks branding.

---

# 22. Database

Initial database tables:

1. users
2. categories
3. products
4. suppliers
5. purchases
6. purchase_items
7. customers
8. sales
9. sale_items
10. payments
11. credit_transactions
12. stock_movements

---

# 23. Core Business Rules

1. Product stock cannot normally become negative.

2. Confirmed purchases increase stock.

3. Confirmed sales decrease stock.

4. Customer returns increase stock where the returned item is resellable.

5. Damaged items decrease available stock.

6. Credit sales create an outstanding customer balance.

7. Customer payments reduce outstanding credit.

8. Dashboard credit is the sum of outstanding balances across customers.

9. Completed transactions should not be silently deleted.

10. Important historical transactions should use reversal/adjustment mechanisms rather than destructive deletion.

11. Deactivated products should remain available in historical transactions.

12. Database foreign-key relationships must maintain referential integrity.

---

# 24. Non-Functional Requirements

The system should be:

* Easy to use
* Responsive
* Reliable
* Secure
* Maintainable
* Fast for normal shop operations
* Easy for a college student to explain

---

# 25. Future Enhancements

Not required for V1:

* Barcode scanner integration
* WhatsApp credit reminders
* SMS notifications
* Online payments
* GST e-invoicing
* Mobile application
* Cloud deployment
* Advanced analytics
* Multi-branch management
* AI recommendations
