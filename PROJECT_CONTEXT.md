# VL Silks – Project Context

## Business

VL Silks is a garment shop.

The software is intended to manage a small shop where garments are purchased from suppliers and sold to customers.

The shop may also sell garments on credit/udhaar.

---

# Core Business Flow

## Purchase

Supplier
→ Purchase
→ Purchase Items
→ Stock Increases

## Sale

Customer
→ Sale
→ Sale Items
→ Stock Decreases

## Credit Sale

Customer
→ Sale
→ Partial Payment
→ Outstanding Credit

## Credit Payment

Customer
→ Payment
→ Credit Balance Decreases

## Return

Customer
→ Return
→ Stock Increases
→ Payment/Credit Adjusted

---

# Most Important Business Metric

Total Credit to Collect.

Example:

Ravi: ₹3,000

Kumar: ₹2,000

Suresh: ₹5,000

Total:

₹10,000

The dashboard must display this value.

---

# Customer Credit Workflow

Customers can have multiple credit transactions.

Example:

1. Credit sale ₹3,000
2. Credit sale ₹2,500
3. Payment ₹1,500
4. Credit sale ₹1,500
5. Payment ₹1,000

The system must preserve this history.

The current outstanding amount is calculated from the transaction history.

---

# Product Model

Garments may differ by:

* Product
* Category
* Size
* Color
* Material

For the initial project, a product record can contain the selected size and color directly.

If the project later requires advanced product variants, the schema can be expanded.

---

# Currency

Use:

INR / ₹

---

# Date

Use Indian business context.

Display dates consistently.

---

# Location

The branding examples may use an Indian address for visual demonstration, but production data should come from actual configured shop information.

Do not hardcode fake customer information into business logic.

---

# Project Philosophy

This project is intentionally:

* Small
* Practical
* Database-focused
* Easy to demonstrate
* Easy to understand
* Visually polished

Do not turn it into an enterprise ERP.
