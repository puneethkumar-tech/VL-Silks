# VL Silks API Specification

## System & Health
GET /api/health

---

## Authentication

POST /api/auth/login

POST /api/auth/logout

GET /api/auth/me

---

## Dashboard

### GET /api/dashboard/summary
Retrieve real-time aggregated shop performance metrics across catalog, sales, returns, and credit.
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "total_products": 12,
      "total_categories": 7,
      "total_variants": 24,
      "total_stock": 1420,
      "low_stock_count": 2,
      "today_sales": 32500.0,
      "today_sales_count": 5,
      "today_returns_amount": 0.0,
      "today_returns_count": 0,
      "today_net_sales": 32500.0,
      "month_sales": 184500.0,
      "month_sales_count": 28,
      "month_returns_amount": 2500.0,
      "month_returns_count": 1,
      "month_net_sales": 182000.0,
      "total_sales_all_time": 425000.0,
      "total_sales_count_all_time": 64,
      "total_credit_to_collect": 45000.0,
      "customers_with_credit": 3,
      "total_credit_limit": 150000.0
    }
  }
  ```

### GET /api/dashboard/recent-sales
Retrieve recent completed sales transactions.
- **Query Params**: `limit` (default: 6)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 6,
    "data": [
      {
        "sale_id": 12,
        "invoice_number": "INV-2026-012",
        "sale_date": "2026-09-26",
        "total_amount": 14500.0,
        "paid_amount": 14500.0,
        "balance_amount": 0.0,
        "payment_status": "PAID",
        "payment_method": "UPI",
        "customer_name": "Meera Sundaram",
        "customer_phone": "9840123456"
      }
    ]
  }
  ```

### GET /api/dashboard/low-stock
Retrieve product variants where stock is below or equal to the minimum threshold.
- **Query Params**: `limit` (default: 15)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 2,
    "data": [
      {
        "variant_id": 4,
        "product_id": 2,
        "product_name": "Kanchipuram Pure Zari Silk Saree",
        "category_name": "Silk Sarees",
        "sku": "KAN-SILK-MRN-01",
        "size": "Free Size",
        "color": "Maroon Gold",
        "stock_quantity": 2,
        "minimum_stock": 5,
        "selling_price": 18500.0
      }
    ]
  }
  ```

### GET /api/dashboard/monthly-sales
Retrieve monthly aggregated sales data for trend charting.
- **Query Params**: `months` (default: 6)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "labels": ["Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026"],
      "sales": [120000.0, 145000.0, 160000.0, 135000.0, 175000.0, 184500.0],
      "paid": [100000.0, 125000.0, 140000.0, 115000.0, 150000.0, 160000.0],
      "credit": [20000.0, 20000.0, 20000.0, 20000.0, 25000.0, 24500.0],
      "counts": [18, 22, 24, 20, 26, 28],
      "details": [...]
    }
  }
  ```

### GET /api/dashboard/top-products
Retrieve top selling garment products ranked by quantity sold and revenue.
- **Query Params**: `limit` (default: 5)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 5,
    "data": [
      {
        "product_id": 1,
        "product_name": "Bridal Pure Kanchipuram Silk",
        "category_name": "Silk Sarees",
        "total_units_sold": 35,
        "total_revenue": 525000.0,
        "orders_count": 28
      }
    ]
  }
  ```

### GET /api/dashboard/category-distribution
Retrieve revenue breakdown across garment categories for donut/pie charting.
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "categories": ["Silk Sarees", "Fancy Sarees", "Cotton Sarees", "Dhotis & Sets"],
      "revenue": [525000.0, 180000.0, 95000.0, 45000.0],
      "units": [35, 45, 60, 30],
      "details": [...]
    }
  }
  ```

---

## Products & Variants

GET /api/products

GET /api/products/:id

POST /api/products

PUT /api/products/:id

DELETE /api/products/:id

GET /api/products/:id/variants

POST /api/products/:id/variants

PUT /api/products/variants/:variant_id

DELETE /api/products/variants/:variant_id

---

## Categories

GET /api/categories

POST /api/categories

PUT /api/categories/:id

DELETE /api/categories/:id

---

## Suppliers

GET /api/suppliers

GET /api/suppliers/:id

POST /api/suppliers

PUT /api/suppliers/:id

DELETE /api/suppliers/:id

---

## Purchases

### GET /api/purchases
Retrieve purchases list with optional query filters.
- **Query Params**: `search` (invoice/supplier), `supplier_id` (int), `status` (PAID, PARTIAL, PENDING), `date_from` (YYYY-MM-DD), `date_to` (YYYY-MM-DD)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 3,
    "purchases": [
      {
        "purchase_id": 1,
        "invoice_number": "PUR-KS-2026-001",
        "supplier_id": 1,
        "supplier_name": "Sri Kanchi Silk Handloom Weavers Society",
        "purchase_date": "2026-09-01",
        "subtotal": 171800.0,
        "discount": 3800.0,
        "tax": 0.0,
        "total": 168000.0,
        "payment_status": "PAID",
        "item_count": 3,
        "total_quantity": 45,
        "created_by_name": "Venkata Lakshmi"
      }
    ]
  }
  ```

### GET /api/purchases/:id
Retrieve single purchase voucher with line items.
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "purchase": {
      "purchase_id": 1,
      "invoice_number": "PUR-KS-2026-001",
      "supplier_name": "Sri Kanchi Silk Handloom Weavers Society",
      "supplier_phone": "9443011223",
      "subtotal": 171800.0,
      "discount": 3800.0,
      "tax": 0.0,
      "total": 168000.0,
      "payment_status": "PAID",
      "items": [
        {
          "purchase_item_id": 1,
          "variant_id": 1,
          "product_name": "Kanchipuram Pure Zari Silk Saree",
          "sku": "KAN-RED-001",
          "size": "Free Size",
          "color": "Crimson Red / Gold Zari",
          "quantity": 15,
          "unit_price": 6500.0,
          "total_price": 97500.0
        }
      ]
    }
  }
  ```

### POST /api/purchases
Atomically record a new inward stock purchase, increment variant inventory stock, and log stock movements. (Admin Only)
- **Request Body**:
  ```json
  {
    "supplier_id": 1,
    "invoice_number": "PUR-2026-101",
    "purchase_date": "2026-09-25",
    "payment_status": "PAID",
    "discount": 100.0,
    "tax": 50.0,
    "notes": "Festival inventory consignment",
    "items": [
      {
        "variant_id": 1,
        "quantity": 10,
        "unit_price": 6500.0
      },
      {
        "variant_id": 2,
        "quantity": 5,
        "unit_price": 6500.0
      }
    ]
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "status": "success",
    "message": "Purchase created successfully and stock updated",
    "purchase_id": 4,
    "invoice_number": "PUR-2026-101",
    "total": 97450.0
  }
  ```

---

## Sales

GET /api/sales

GET /api/sales/:id

POST /api/sales

---

## Customers

### GET /api/customers
Retrieve customer directory with purchase statistics and search filtering.
- **Access**: Public / Staff / Admin
- **Query Params**: `search` (name/phone/email), `phone` (phone filter), `status` (ACTIVE, INACTIVE)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 4,
    "data": [
      {
        "customer_id": 1,
        "customer_name": "Smt. Shanti Devi",
        "phone": "9845012345",
        "email": "shanti.devi@gmail.com",
        "address": "Flat 302, Sai Residency, 4th Cross, Malleshwaram, Bangalore",
        "credit_limit": 25000.0,
        "status": "ACTIVE",
        "total_purchases": 2,
        "total_purchase_value": 44498.0,
        "total_paid": 30000.0,
        "outstanding_balance": 14498.0
      }
    ]
  }
  ```

### GET /api/customers/:id
Retrieve single customer profile, aggregated financial metrics, and invoice history.
- **Access**: Public / Staff / Admin
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "data": {
      "customer_id": 1,
      "customer_name": "Smt. Shanti Devi",
      "phone": "9845012345",
      "email": "shanti.devi@gmail.com",
      "address": "Flat 302, Sai Residency, 4th Cross, Malleshwaram, Bangalore",
      "credit_limit": 25000.0,
      "status": "ACTIVE",
      "total_purchases": 2,
      "total_purchase_value": 44498.0,
      "total_paid": 30000.0,
      "outstanding_balance": 14498.0,
      "available_credit": 10502.0
    },
    "purchases": [
      {
        "sale_id": 1,
        "invoice_number": "SALE-2026-0001",
        "sale_date": "2026-09-02",
        "subtotal": 24998.0,
        "discount": 0.0,
        "tax": 0.0,
        "total_amount": 24998.0,
        "paid_amount": 10000.0,
        "balance_amount": 14998.0,
        "payment_method": "SPLIT",
        "payment_status": "PARTIAL",
        "item_count": 2,
        "total_quantity": 2,
        "created_by_name": "Venkata Lakshmi"
      }
    ]
  }
  ```

### POST /api/customers
Register a new customer with validation.
- **Access**: Admin Only
- **Request Body**:
  ```json
  {
    "customer_name": "Smt. Parvathi Ammal",
    "phone": "9845112233",
    "email": "parvathi.ammal@example.com",
    "address": "12 Temple Street, Kanchipuram",
    "credit_limit": 30000.0,
    "status": "ACTIVE"
  }
  ```
- **Validation**: `customer_name` required, `phone` required and globally unique, `email` valid format if provided.
- **Response**: `201 Created`
  ```json
  {
    "status": "success",
    "message": "Customer created successfully",
    "customer_id": 5,
    "data": {
      "customer_id": 5,
      "customer_name": "Smt. Parvathi Ammal",
      "phone": "9845112233",
      "credit_limit": 30000.0,
      "status": "ACTIVE"
    }
  }
  ```

### PUT /api/customers/:id
Update customer details without affecting historical transactions.
- **Access**: Admin Only
- **Request Body**:
  ```json
  {
    "customer_name": "Smt. Parvathi Ammal",
    "phone": "9845112233",
    "email": "parvathi.updated@example.com",
    "address": "12 Temple Street, Kanchipuram",
    "credit_limit": 35000.0,
    "status": "ACTIVE"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "message": "Customer updated successfully",
    "data": {
      "customer_id": 5,
      "customer_name": "Smt. Parvathi Ammal",
      "phone": "9845112233"
    }
  }
  ```

### DELETE /api/customers/:id
Safely deactivate a customer.
- **Access**: Admin Only
- **Behavior**: Sets `status = 'INACTIVE'`. Strictly preserves all historical sales, sale items, payments, and credit transactions.
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "message": "Customer #5 safely deactivated. Historical records preserved."
  }
  ```

### GET /api/pos/customers/search
Live customer search for POS checkout with available credit limits.
- **Query Params**: `q` (search term)
- **Response**: `200 OK`

### POST /api/pos/customers/quick-create
Quickly register customer from POS modal.
- **Request Body**: `customer_name`, `phone`, `credit_limit` (optional), `email` (optional), `address` (optional)
- **Response**: `201 Created`

---

## Credit / Udhaar

### GET /api/credit/summary
Retrieve system-wide aggregated credit & Udhaar management metrics.
- **Access**: Public / Staff / Admin
- **Response**: `200 OK`

### GET /api/credit/customers
Retrieve directory of customers with outstanding Udhaar balances.
- **Access**: Public / Staff / Admin
- **Query Params**: `search` (name/phone), `status` (ACTIVE/INACTIVE/ALL), `min_balance` (number)
- **Response**: `200 OK`

### GET /api/credit/customer/:id
Retrieve comprehensive credit profile and utilization statistics for a single customer.
- **Access**: Public / Staff / Admin
- **Response**: `200 OK`

### GET /api/credit/customer/:id/history
Retrieve complete chronological debit/credit transaction ledger with running balances.
- **Access**: Public / Staff / Admin
- **Response**: `200 OK`

### POST /api/credit/customer/:id/payment
Record an atomic settlement payment against customer's outstanding Udhaar.
- **Access**: Authenticated Staff / Admin
- **Request Body**: `amount`, `payment_method` (CASH/UPI/CARD/BANK_TRANSFER), `reference_number` (optional), `notes` (optional)
- **Response**: `201 Created`

---

## PDF Generation & Downloads

### GET /api/pdf/credit/:customer_id
Generate and stream a branded, print-ready customer Credit / Udhaar Statement PDF.
- **Access**: Authenticated Staff / Admin
- **Path Parameter**: `customer_id` (integer) – target customer ID
- **Query Parameters**:
  - `date_from` (string, optional, format: `YYYY-MM-DD`) – Filter transactions from this date
  - `date_to` (string, optional, format: `YYYY-MM-DD`) – Filter transactions up to this date
- **Response**:
  - `200 OK`: Binary PDF stream
    - **Content-Type**: `application/pdf`
    - **Content-Disposition**: `attachment; filename="VL-Silks-Credit-Statement-<Name>-ID<id>.pdf"`
  - `400 Bad Request`: When `date_from` / `date_to` are malformed or `date_from > date_to`
  - `401 Unauthorized`: When user is not authenticated
  - `404 Not Found`: When customer ID does not exist
  - `500 Internal Server Error`: When unexpected PDF generation error occurs
- **Example Requests**:
  - `GET /api/pdf/credit/1` (Full historical statement)
  - `GET /api/pdf/credit/1?date_from=2026-09-01&date_to=2026-09-25` (Period statement)

---

## Inventory

### GET /api/inventory
Retrieve all inventory items with computed stock health statuses and query filtering.
- **Query Params**: `search` (name, SKU, brand, color, barcode), `category_id` (int), `status` (ACTIVE, INACTIVE), `stock_status` (IN_STOCK, LOW_STOCK, OUT_OF_STOCK)
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 24,
    "inventory": [
      {
        "variant_id": 1,
        "product_id": 1,
        "product_name": "Kanchipuram Pure Zari Silk Saree",
        "brand": "VL Silks",
        "category_id": 1,
        "category_name": "Silk Sarees",
        "sku": "SKU-KAN-RED",
        "size": "Free Size",
        "color": "Crimson Red / Gold Zari",
        "barcode": "8901001001",
        "purchase_price": 6500.0,
        "selling_price": 9999.0,
        "stock_quantity": 26,
        "minimum_stock": 5,
        "stock_status": "IN_STOCK"
      }
    ]
  }
  ```

### GET /api/inventory/low-stock
Retrieve active variants where current stock is positive but at or below minimum threshold (`0 < stock <= min_stock`).
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 2,
    "low_stock_items": [
      {
        "variant_id": 5,
        "product_name": "Banarasi Katan Silk Saree",
        "sku": "SKU-BAN-MST",
        "stock_quantity": 2,
        "minimum_stock": 3,
        "units_needed": 1,
        "stock_status": "LOW_STOCK"
      }
    ]
  }
  ```

### GET /api/inventory/movements
Retrieve chronological audit log of inventory stock movements.
- **Query Params**: `variant_id` (int), `movement_type` (PURCHASE, SALE, ADJUSTMENT, DAMAGE, OPENING, CUSTOMER_RETURN), `date_from` (YYYY-MM-DD), `date_to` (YYYY-MM-DD), `search`
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "count": 15,
    "movements": [
      {
        "movement_id": 15,
        "variant_id": 1,
        "product_name": "Kanchipuram Pure Zari Silk Saree",
        "sku": "SKU-KAN-RED",
        "movement_type": "PURCHASE",
        "quantity": 15,
        "reference_type": "PURCHASE",
        "reference_id": 1,
        "notes": "Inward stock via Purchase #PUR-KS-2026-001 (15 units)",
        "movement_date": "2026-09-01 09:00:00",
        "created_by_name": "Venkata Lakshmi"
      }
    ]
  }
  ```

### POST /api/inventory/adjustment
Atomically adjust variant stock or record damaged stock write-off (Admin Only).
- **Request Body (Manual Adjustment)**:
  ```json
  {
    "variant_id": 1,
    "adjustment_type": "INCREASE",
    "quantity": 5,
    "reason": "Physical stock audit recount surplus"
  }
  ```
- **Request Body (Damaged Stock)**:
  ```json
  {
    "variant_id": 1,
    "adjustment_type": "DAMAGE",
    "quantity": 2,
    "reason": "Water damage during roof leakage"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "status": "success",
    "message": "Stock adjusted successfully and audit record created",
    "data": {
      "variant_id": 1,
      "sku": "SKU-KAN-RED",
      "product_name": "Kanchipuram Pure Zari Silk Saree",
      "previous_stock": 26,
      "delta": 5,
      "new_stock": 31,
      "movement_type": "ADJUSTMENT"
    }
  }
  ```

---

## Returns & Exchanges

GET /api/returns
  — List all returns with filtering (search, refund_type, date_from, date_to)
  — Returns: { status, count, data: [return] }

GET /api/returns/:id
  — Retrieve a single return with all return items
  — Returns: { status, data: { return_id, return_reference, sale_id, invoice_number, customer_id, customer_name, return_date, return_reason, total_refund_amount, refund_type, items: [] } }
  — 404 if not found

GET /api/returns/sale/:sale_id/returnable-items
  — Calculate returnable quantity breakdown per line item for an invoice
  — Returns: { status, sale: {…}, count, items: [{ sale_item_id, variant_id, sold_quantity, already_returned_quantity, returnable_quantity, effective_unit_price, is_returnable, … }] }
  — 404 if sale not found

POST /api/returns
  — Atomic customer garment return
  — Body: { sale_id, refund_type (CASH|CREDIT_ADJUSTMENT|EXCHANGE), return_date, return_reason, items: [{ sale_item_id, quantity, condition_status (RESTOCKABLE|DAMAGED) }] }
  — Returns 201: { status, message, data: { return_id, return_reference, total_refund_amount, refund_type, item_count } }
  — Returns 400: ValidationError (over-quantity, invalid sale, bad refund_type, CREDIT_ADJUSTMENT without customer)

POST /api/returns/exchange
  — Atomic garment exchange (return old + issue replacement)
  — Body: { sale_id, return_date, notes, payment_method, old_items: [{ sale_item_id, quantity, condition_status }], new_items: [{ variant_id, quantity }] }
  — Returns 201: { status, message, data: { return_id, return_reference, old_total_value, new_total_value, price_difference, payment_status (CUSTOMER_OWES|STORE_OWES|EVEN_EXCHANGE) } }
  — Returns 400: ValidationError (insufficient new stock, already-returned item, inactive variant)


## Reports

GET /api/reports/sales

GET /api/reports/purchases

GET /api/reports/inventory

GET /api/reports/credit

GET /api/reports/profit

---

## PDF Export

GET /api/pdf/sales/:id

GET /api/pdf/purchase/:id

GET /api/pdf/credit/:customer_id
