# System Workflows & Algorithms
## VL Silks - Core Business Algorithms & Transaction Workflows
---
## 1. Point of Sale (POS) Checkout Workflow
```
Algorithm: ProcessSaleCheckout
Input: customer_id (optional), items [{variant_id, quantity, unit_price, discount}], 
       payment_method, paid_amount, notes, created_by_user_id
1. BEGIN DATABASE TRANSACTION
2. For each item in items:
     a. Fetch variant record with row lock: SELECT stock_quantity, selling_price FROM product_variants WHERE variant_id = ? FOR UPDATE
     b. IF variant does not exist: ROLLBACK, raise NotFoundError
     c. IF variant.stock_quantity < item.quantity: ROLLBACK, raise InsufficientStockError
3. Compute Financial Totals (using Decimal arithmetic):
     a. subtotal = SUM(item.quantity * item.unit_price)
     b. total_discount = SUM(item.discount)
     c. tax = 0.00 (or applicable tax rate)
     d. total_amount = subtotal - total_discount + tax
     e. balance_amount = total_amount - paid_amount
4. IF balance_amount > 0 (Credit/Udhaar sale):
     a. IF customer_id is NULL: ROLLBACK, raise CustomerRequiredForCreditError
     b. Fetch customer: current_balance = GetCustomerOutstandingBalance(customer_id)
     c. IF (current_balance + balance_amount) > customer.credit_limit:
          ROLLBACK, raise CreditLimitExceededError
5. Generate unique invoice number: SALE-YYYY-NNNN
6. INSERT INTO sales (customer_id, invoice_number, sale_date, subtotal, discount, tax, total_amount, paid_amount, balance_amount, payment_method, payment_status, created_by)
7. For each item in items:
     a. INSERT INTO sale_items (sale_id, variant_id, quantity, unit_price, discount, total_price)
     b. UPDATE product_variants SET stock_quantity = stock_quantity - item.quantity WHERE variant_id = item.variant_id
     c. INSERT INTO stock_movements (variant_id, movement_type='SALE', quantity=-item.quantity, reference_type='SALE', reference_id=sale_id, created_by)
8. IF paid_amount > 0:
     a. INSERT INTO payments (customer_id, sale_id, amount=paid_amount, payment_method, payment_date, created_by)
9. IF balance_amount > 0:
     a. running_balance = current_balance + balance_amount
     b. INSERT INTO credit_transactions (customer_id, sale_id, transaction_type='CREDIT_SALE', amount=balance_amount, running_balance=running_balance, transaction_date, created_by)
10. COMMIT TRANSACTION
11. Return created sale record and invoice number
```
---
## 2. Customer Return & Restocking Workflow
```
Algorithm: ProcessCustomerReturn
Input: sale_id, return_items [{variant_id, quantity, condition_status}], refund_type, return_reason, created_by_user_id
1. BEGIN DATABASE TRANSACTION
2. Verify sale exists: SELECT * FROM sales WHERE sale_id = ?
3. For each item in return_items:
     a. Fetch original sale_item: SELECT quantity, unit_price FROM sale_items WHERE sale_id = ? AND variant_id = ?
     b. Fetch already returned count: SELECT COALESCE(SUM(quantity), 0) FROM return_items WHERE sale_item_id = ?
     c. remaining_returnable = original_quantity - already_returned
     d. IF item.quantity > remaining_returnable:
          ROLLBACK, raise OverReturnError("Cannot return more items than originally purchased")
4. Compute total_refund_amount = SUM(item.quantity * original_unit_price)
5. INSERT INTO returns (sale_id, customer_id, return_date, return_reason, total_refund_amount, refund_type, created_by)
6. For each item in return_items:
     a. item_refund = item.quantity * original_unit_price
     b. INSERT INTO return_items (return_id, sale_item_id, variant_id, quantity, unit_price, refund_amount, condition_status)
     c. IF item.condition_status == 'RESTOCKABLE':
          i. UPDATE product_variants SET stock_quantity = stock_quantity + item.quantity WHERE variant_id = item.variant_id
          ii. INSERT INTO stock_movements (variant_id, movement_type='CUSTOMER_RETURN', quantity=item.quantity, reference_type='RETURN', reference_id=return_id, created_by)
     d. IF item.condition_status == 'DAMAGED':
          i. Do NOT increment variant stock
          ii. INSERT INTO stock_movements (variant_id, movement_type='DAMAGE', quantity=0, reference_type='RETURN', reference_id=return_id, notes="Returned Damaged", created_by)
7. IF refund_type == 'CREDIT_ADJUSTMENT' AND sale.customer_id is NOT NULL:
     a. current_balance = GetCustomerOutstandingBalance(sale.customer_id)
     b. running_balance = current_balance - total_refund_amount
     c. INSERT INTO credit_transactions (customer_id, sale_id, transaction_type='RETURN_REFUND', amount=-total_refund_amount, running_balance=running_balance, transaction_date, created_by)
8. COMMIT TRANSACTION
9. Return return_id and refund summary
```
---
## 3. Credit Settlement Payment Workflow
```
Algorithm: ProcessCreditSettlement
Input: customer_id, payment_amount, payment_method, reference_number, notes, created_by_user_id
1. BEGIN DATABASE TRANSACTION
2. Fetch customer: current_balance = GetCustomerOutstandingBalance(customer_id)
3. IF payment_amount <= 0: ROLLBACK, raise InvalidAmountError
4. IF payment_amount > current_balance:
     ROLLBACK, raise OverpaymentError("Payment amount exceeds outstanding balance of " + current_balance)
5. INSERT INTO payments (customer_id, amount=payment_amount, payment_method, payment_date=TODAY, reference_number, notes, created_by)
6. new_running_balance = current_balance - payment_amount
7. INSERT INTO credit_transactions (customer_id, payment_id=new_payment_id, transaction_type='PAYMENT', amount=-payment_amount, running_balance=new_running_balance, transaction_date=TODAY, notes, created_by)
8. COMMIT TRANSACTION
9. Return payment receipt and new outstanding balance
```
