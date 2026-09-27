# Entity-Relationship Diagram
## VL Silks - Database Entity-Relationship Reference (15 Tables)
---
## 1. Mermaid ER Diagram
```mermaid
erDiagram
    users {
        int user_id PK
        varchar name
        varchar email UK
        varchar password_hash
        enum role
        enum status
        timestamp created_at
        timestamp updated_at
    }
    categories {
        int category_id PK
        varchar category_name UK
        text description
        enum status
        timestamp created_at
        timestamp updated_at
    }
    products {
        int product_id PK
        int category_id FK
        varchar product_name
        varchar brand
        varchar material
        text description
        enum status
        timestamp created_at
        timestamp updated_at
    }
    product_variants {
        int variant_id PK
        int product_id FK
        varchar sku UK
        varchar size
        varchar color
        decimal purchase_price
        decimal selling_price
        int stock_quantity
        int minimum_stock
        varchar barcode UK
        enum status
        timestamp created_at
        timestamp updated_at
    }
    suppliers {
        int supplier_id PK
        varchar supplier_name
        varchar contact_person
        varchar phone
        varchar email
        text address
        varchar gst_number
        enum status
        timestamp created_at
        timestamp updated_at
    }
    purchases {
        int purchase_id PK
        int supplier_id FK
        varchar invoice_number
        date purchase_date
        decimal subtotal
        decimal discount
        decimal tax
        decimal total
        enum payment_status
        text notes
        int created_by FK
        timestamp created_at
        timestamp updated_at
    }
    purchase_items {
        int purchase_item_id PK
        int purchase_id FK
        int variant_id FK
        int quantity
        decimal unit_price
        decimal total_price
        timestamp created_at
    }
    customers {
        int customer_id PK
        varchar customer_name
        varchar phone UK
        varchar email
        text address
        decimal credit_limit
        enum status
        timestamp created_at
        timestamp updated_at
    }
    sales {
        int sale_id PK
        int customer_id FK
        varchar invoice_number UK
        date sale_date
        decimal subtotal
        decimal discount
        decimal tax
        decimal total_amount
        decimal paid_amount
        decimal balance_amount
        enum payment_method
        enum payment_status
        text notes
        int created_by FK
        timestamp created_at
        timestamp updated_at
    }
    sale_items {
        int sale_item_id PK
        int sale_id FK
        int variant_id FK
        int quantity
        decimal unit_price
        decimal discount
        decimal total_price
        timestamp created_at
    }
    payments {
        int payment_id PK
        int customer_id FK
        int sale_id FK
        decimal amount
        enum payment_method
        date payment_date
        varchar reference_number
        text notes
        int created_by FK
        timestamp created_at
    }
    credit_transactions {
        int transaction_id PK
        int customer_id FK
        int sale_id FK
        int payment_id FK
        enum transaction_type
        decimal amount
        decimal running_balance
        date transaction_date
        text notes
        int created_by FK
        timestamp created_at
    }
    stock_movements {
        int movement_id PK
        int variant_id FK
        enum movement_type
        int quantity
        enum reference_type
        int reference_id
        text notes
        timestamp movement_date
        int created_by FK
        timestamp created_at
    }
    returns {
        int return_id PK
        int sale_id FK
        int customer_id FK
        date return_date
        text return_reason
        decimal total_refund_amount
        enum refund_type
        int created_by FK
        timestamp created_at
    }
    return_items {
        int return_item_id PK
        int return_id FK
        int sale_item_id FK
        int variant_id FK
        int quantity
        decimal unit_price
        decimal refund_amount
        enum condition_status
        timestamp created_at
    }
    categories ||--o{ products : "categorizes"
    products ||--o{ product_variants : "has_variants"
    suppliers ||--o{ purchases : "supplies"
    purchases ||--o{ purchase_items : "contains"
    product_variants ||--o{ purchase_items : "purchased_in"
    customers ||--o{ sales : "places"
    sales ||--o{ sale_items : "includes"
    product_variants ||--o{ sale_items : "sold_in"
    customers ||--o{ payments : "makes"
    sales ||--o| payments : "settled_via"
    customers ||--o{ credit_transactions : "maintains_ledger"
    sales ||--o| credit_transactions : "generates_credit"
    payments ||--o| credit_transactions : "reduces_credit"
    product_variants ||--o{ stock_movements : "tracked_by"
    sales ||--o{ returns : "originates"
    customers ||--o{ returns : "requests"
    returns ||--o{ return_items : "contains"
    sale_items ||--o{ return_items : "returned_item"
    product_variants ||--o{ return_items : "restocked_as"
    users ||--o{ purchases : "creates"
    users ||--o{ sales : "bills"
    users ||--o{ payments : "records"
    users ||--o{ credit_transactions : "creates"
    users ||--o{ stock_movements : "audits"
    users ||--o{ returns : "authorizes"
```
---
## 2. Table Relationships & Cardinality
| Parent Table | Child Table | Foreign Key | Cardinality | Delete Action | Business Meaning |
|---|---|---|---|---|---|
| `categories` | `products` | `category_id` | 1 : N | RESTRICT | Categories cannot be deleted while products belong to them |
| `products` | `product_variants` | `product_id` | 1 : N | RESTRICT | Products cannot be deleted while variants exist |
| `suppliers` | `purchases` | `supplier_id` | 1 : N | RESTRICT | Suppliers with purchase records are retained for accounting |
| `purchases` | `purchase_items` | `purchase_id` | 1 : N | CASCADE | Deleting a purchase deletes all its line items |
| `product_variants` | `purchase_items` | `variant_id` | 1 : N | RESTRICT | Variants with purchase history cannot be dropped |
| `customers` | `sales` | `customer_id` | 1 : N | SET NULL | Walk-in sales have NULL customer; customer deactivation preserves sales |
| `sales` | `sale_items` | `sale_id` | 1 : N | CASCADE | Deleting a sale cascades to its line items |
| `product_variants` | `sale_items` | `variant_id` | 1 : N | RESTRICT | Variants with sales history are protected |
| `customers` | `payments` | `customer_id` | 1 : N | RESTRICT | Customers with payment records cannot be deleted |
| `sales` | `payments` | `sale_id` | 1 : N | SET NULL | Payments linked to sales persist even if sale is decoupled |
| `customers` | `credit_transactions`| `customer_id` | 1 : N | RESTRICT | Credit ledger history must be permanently preserved |
| `sales` | `credit_transactions`| `sale_id` | 1 : N | SET NULL | Credit debits link to sales |
| `payments` | `credit_transactions`| `payment_id` | 1 : N | SET NULL | Credit credits link to settlement payments |
| `product_variants` | `stock_movements` | `variant_id` | 1 : N | RESTRICT | Complete audit history is preserved |
| `sales` | `returns` | `sale_id` | 1 : N | RESTRICT | Returns must link to a valid historical sale |
| `customers` | `returns` | `customer_id` | 1 : N | SET NULL | Returns retain customer association |
| `returns` | `return_items` | `return_id` | 1 : N | CASCADE | Return items cascade with the return header |
| `sale_items` | `return_items` | `sale_item_id` | 1 : N | SET NULL | Links returned line to original billed line item |
| `product_variants` | `return_items` | `variant_id` | 1 : N | RESTRICT | Preserves variant link for restocking/damage |
| `users` | `*` (6 tables) | `created_by` | 1 : N | RESTRICT | Full audit trail of which user performed each transaction |
