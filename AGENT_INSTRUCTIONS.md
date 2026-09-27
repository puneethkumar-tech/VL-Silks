# VL Silks – Agent Instructions

## Role

You are working as a software engineering agent on the VL Silks project.

Before making changes, read:

1. README.md
2. PRD.md
3. PROJECT_CONTEXT.md
4. DESIGN_CONTEXT.md
5. DATABASE_DESIGN.md
6. TODO.md

Do not make architectural decisions that conflict with these documents without explaining the reason.

---

# Project Goal

Build:

VL Silks – Garment Shop Inventory, Sales & Credit Management System

This is primarily a college DBMS project.

The project should be realistic but simple enough to understand and demonstrate.

---

# Technology Rules

Use:

Frontend:

* HTML
* CSS
* JavaScript
* Bootstrap

Backend:

* Python
* Flask

Database:

* MySQL

PDF:

* ReportLab

Do not introduce a new framework unless there is a clear reason.

---

# Engineering Principles

Prefer:

* Simple code
* Readable code
* Small functions
* Reusable components
* Clear naming
* Proper validation
* Proper database relationships
* Parameterized SQL
* Secure password hashing
* Transactions for important operations
* Error handling

Avoid:

* Overengineering
* Unnecessary abstractions
* Unnecessary dependencies
* Duplicate code
* Hardcoded business data
* Hardcoded credentials
* Plain-text passwords

---

# Database Rules

Never bypass the database design just to make a feature work.

Maintain:

* Primary keys
* Foreign keys
* Constraints
* Referential integrity

Important transactions such as sales and purchases should update related stock records safely.

---

# Inventory Rule

A sale must decrease stock.

A purchase must increase stock.

A return must update stock appropriately.

A damaged item must reduce available stock.

Do not allow accidental negative inventory unless the business rule explicitly supports it.

---

# Credit Rule

Credit belongs to a customer.

A credit sale increases outstanding balance.

A payment reduces outstanding balance.

The dashboard must calculate total outstanding credit across all customers.

Customer credit history must remain traceable.

---

# UI Rules

Follow DESIGN_CONTEXT.md.

Always use VL Silks branding.

Primary:
#8B0000

Secondary:
#D4AF37

Background:
#FFF8E1

Text:
#333333

Do not introduce random branding colors.

---

# PDF Rules

Generated PDFs must use:

* VL Silks name
* VL Silks logo
* Tagline
* Professional layout
* INR currency
* Clear dates
* Customer information
* Correct totals

Never generate a PDF with fake or placeholder transaction data in production code.

---

# Before Coding

1. Understand the existing architecture.
2. Inspect existing files.
3. Check database schema.
4. Check current TODO.
5. Reuse existing components where possible.
6. Do not rewrite working functionality unnecessarily.

---

# After Coding

Run appropriate checks.

At minimum:

* Application starts
* Database connection works
* No syntax errors
* Main feature works
* Existing functionality still works

Update TODO.md when a feature is completed.

Update CHANGELOG.md for meaningful changes.

---

# Important

Do not mark a feature as complete unless it has been implemented and tested.

If something is uncertain, state the uncertainty instead of inventing behavior.

Do not silently change project requirements.

