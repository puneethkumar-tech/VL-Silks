# VL Silks

## Garment Shop Inventory, Sales & Credit Management System

VL Silks is a small-business management system designed for a garment shop.

The system manages products, inventory, suppliers, purchases, sales, customers, credit/udhaar, payments, returns, reports, and customer credit statements.

The project is primarily designed as a college DBMS project while maintaining a realistic real-world business workflow.

---

## Brand

**Shop Name:** VL Silks

**Tagline:** TRADITION MEETS FASHION

**Brand Style:** Premium Indian garment/silk shop

**Primary Color:** Maroon / Burgundy

**Secondary Color:** Gold

**Background:** Warm Cream

**Text:** Dark Charcoal

---

## Core Technology

### Frontend

* HTML
* CSS
* JavaScript
* Bootstrap

### Backend

* Python
* Flask

### Database

* MySQL

### PDF

* ReportLab

### Development

* VS Code
* Git
* GitHub
* MySQL Workbench

---

## Main Modules

1. Authentication
2. Dashboard
3. Products
4. Categories
5. Inventory
6. Suppliers
7. Purchases
8. Sales & Billing
9. Customers
10. Credit / Udhaar
11. Credit Payments
12. Credit History
13. PDF Credit Statements
14. Returns / Exchanges
15. Reports
16. User Management

---

## Main Business Goal

The system should allow VL Silks to replace manual stock and credit notebooks with a centralized digital system.

The most important business information is:

* What products are available?
* How much stock is available?
* What was sold?
* What was purchased?
* Which customers owe money?
* How much money is owed in total?
* What is the complete credit history of each customer?
* Can a customer credit statement be exported as PDF?

---

## Important Dashboard Information

The dashboard must show:

* Total Products
* Total Stock
* Today's Sales
* Today's Purchases
* Total Credit to Collect
* Number of Customers With Credit
* Low Stock Products
* Recent Sales
* Monthly Sales

The "Credit to Collect" value represents the total outstanding amount across all customers.

---

## Important Rule

Do not over-engineer this project.

This is a college-level project.

Prefer:

* Simple architecture
* Clear database relationships
* Easy-to-understand code
* Maintainable code
* Good UI
* Correct business logic

Avoid unnecessary:

* Microservices
* Kubernetes
* Redis
* Complex cloud infrastructure
* AI features
* Payment gateways
* Unnecessary external services

---

## Project Status: Core Application Completed (Phases 0–18 Verified + E2E QA Passed)

All core business modules, transactional workflows, and college documentation have been fully implemented and verified:
- **Pytest Suite:** 390 tests collected: 388 passed, 2 skipped across 16 test modules
- **E2E Playwright QA:** 13 / 13 smoke tests passed (Desktop, Laptop, Mobile viewports; POS, Invoice, Credit PDF, Returns, Reports 5/5, RBAC)
- **Database:** 15 normalized tables (3NF) with MySQL InnoDB ACID transactions & check constraints
- **Test DB Isolation:** `vl_silks_test_db` used for all mutating browser workflows; `vl_silks_db` (demo) remained untouched throughout the full QA cycle
- **Documentation:** Complete college submission report [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) and specialized references in `docs/`
- **Scope Note:** Core authentication, RBAC, and responsive UI components are fully verified; minor non-essential UI polish items (e.g., custom SVG empty state graphics, generic reusable delete modals) are noted in `TODO.md`.

---

## College Documentation Index

- **[Unified Project Documentation](PROJECT_DOCUMENTATION.md)** - Master college report organizing all modules, architecture, schema, and tests.

### Specialized Documentation Files (`docs/`):
1. **[Project Abstract](docs/PROJECT_ABSTRACT.md)** - Executive summary, keywords, and real-world background.
2. **[Problem Statement](docs/PROBLEM_STATEMENT.md)** - Manual system limitations, objectives, and proposed solutions.
3. **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)** - 3-Tier architecture diagram, components, and design patterns.
4. **[ER Diagram](docs/ER_DIAGRAM.md)** - Complete 15-table Mermaid entity-relationship diagram & relationships.
5. **[Data Flow Diagram (DFD)](docs/DFD.md)** - Level 0, Level 1, and Level 2 transaction data flow diagrams.
6. **[Database Schema](docs/DATABASE_SCHEMA.md)** - Complete 15-table column reference, types, keys, and indexes.
7. **[Database Normalization](docs/NORMALIZATION.md)** - Formal analysis and proofs for 1NF, 2NF, and 3NF normalization.
8. **[Module Specifications](docs/MODULES.md)** - Route endpoints, templates, and service responsibilities.
9. **[Security & Data Integrity](docs/SECURITY.md)** - Scrypt hashing, RBAC decorators, SQLi prevention, Decimal precision.
10. **[Testing & QA](docs/TESTING.md)** - Test suite breakdown, negative testing, and test methodology.
11. **[System Workflows](docs/WORKFLOWS.md)** - Step-by-step algorithms for POS checkout, Returns, and Credit settlements.
12. **[Comprehensive Viva Voce Guide](docs/VIVA_QA.md)** - 60 Viva questions & answers across 10 technical sections.

---

## How to Run the Project

### 1. Setup Virtual Environment & Install Dependencies
```bash
python -m venv .venv
.venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Install development and testing dependencies (pytest, playwright)
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set your MySQL database credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=vl_silks_db
TEST_DB_NAME=vl_silks_test_db
DB_USER=root
DB_PASSWORD=your_mysql_password
SECRET_KEY=your_secret_key_here
```

### 3. Initialize Databases
Import development/demo schema and seed data:
```bash
mysql -u root -p vl_silks_db < database/schema.sql
mysql -u root -p vl_silks_db < database/seed.sql
```

Provision the isolated test database:
```bash
python database/setup_test_db.py
```

### 4. Run the Application
```bash
python -m backend.app
```
Access the application at `http://127.0.0.1:5000`

### 5. Run Automated Tests
```bash
pytest
```
