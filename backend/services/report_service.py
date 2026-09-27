import csv
import io
from decimal import Decimal
from datetime import date, datetime
from backend.utils.database import query_db


def _to_decimal(val, default=Decimal('0.00')):
    if val is None:
        return default
    try:
        return Decimal(str(val)).quantize(Decimal('0.01'))
    except Exception:
        return default


def _fmt_date(d):
    if isinstance(d, (date, datetime)):
        return d.strftime('%Y-%m-%d')
    return str(d) if d is not None else ''


def _default_date_range():
    today = date.today()
    start = today.replace(day=1)
    return start.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')


def get_sales_report(start_date=None, end_date=None):
    if not start_date or not end_date:
        start_date, end_date = _default_date_range()
    rows = query_db(
        """SELECT s.sale_id, s.invoice_number, s.sale_date,
               COALESCE(c.customer_name, 'Walk-in Customer') AS customer_name,
               COALESCE(c.phone, '') AS customer_phone,
               s.total_amount, s.discount, s.paid_amount,
               s.balance_amount, s.payment_status, s.payment_method,
               COUNT(si.sale_item_id) AS item_count,
               COALESCE(SUM(si.quantity), 0) AS units_sold
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        LEFT JOIN sale_items si ON s.sale_id = si.sale_id
        WHERE s.sale_date BETWEEN %s AND %s
        GROUP BY s.sale_id, s.invoice_number, s.sale_date,
                 c.customer_name, c.phone, s.total_amount, s.discount,
                 s.paid_amount, s.balance_amount, s.payment_status, s.payment_method
        ORDER BY s.sale_date DESC, s.sale_id DESC""",
        (start_date, end_date)) or []
    sales = []
    total_revenue = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_credit = Decimal('0.00')
    total_discount = Decimal('0.00')
    total_units = 0
    for r in rows:
        rev = _to_decimal(r['total_amount'])
        paid = _to_decimal(r['paid_amount'])
        bal = _to_decimal(r['balance_amount'])
        disc = _to_decimal(r['discount'])
        units = int(r['units_sold'] or 0)
        total_revenue += rev
        total_paid += paid
        total_credit += bal
        total_discount += disc
        total_units += units
        sales.append({'sale_id': r['sale_id'], 'invoice_number': r['invoice_number'],
            'sale_date': _fmt_date(r['sale_date']), 'customer_name': r['customer_name'],
            'customer_phone': r['customer_phone'], 'total_amount': float(rev),
            'discount_amount': float(disc), 'paid_amount': float(paid),
            'balance_amount': float(bal), 'payment_status': r['payment_status'],
            'payment_method': r['payment_method'], 'item_count': int(r['item_count'] or 0),
            'units_sold': units})
    pm_rows = query_db(
        """SELECT payment_method, COUNT(*) AS invoice_count,
               COALESCE(SUM(total_amount), 0) AS revenue
        FROM sales WHERE sale_date BETWEEN %s AND %s
        GROUP BY payment_method ORDER BY revenue DESC""",
        (start_date, end_date)) or []
    payment_breakdown = [{'payment_method': r['payment_method'],
        'invoice_count': int(r['invoice_count']),
        'revenue': float(_to_decimal(r['revenue']))} for r in pm_rows]
    return {'start_date': start_date, 'end_date': end_date, 'sales': sales,
        'summary': {'invoice_count': len(sales), 'total_revenue': float(total_revenue),
            'total_paid': float(total_paid), 'total_credit': float(total_credit),
            'total_discount': float(total_discount), 'total_units_sold': total_units},
        'payment_breakdown': payment_breakdown}


def export_sales_report_csv(start_date=None, end_date=None):
    data = get_sales_report(start_date, end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Invoice No.', 'Sale Date', 'Customer', 'Phone', 'Total',
        'Discount', 'Paid', 'Balance', 'Status', 'Payment Method', 'Items', 'Units Sold'])
    for s in data['sales']:
        writer.writerow([s['invoice_number'], s['sale_date'], s['customer_name'],
            s['customer_phone'], s['total_amount'], s['discount_amount'],
            s['paid_amount'], s['balance_amount'], s['payment_status'],
            s['payment_method'], s['item_count'], s['units_sold']])
    writer.writerow([])
    sm = data['summary']
    writer.writerow(['TOTAL', '', '', '', sm['total_revenue'], sm['total_discount'],
        sm['total_paid'], sm['total_credit'], '', '', sm['invoice_count'], sm['total_units_sold']])
    return output.getvalue().encode('utf-8-sig')


def get_purchase_report(start_date=None, end_date=None):
    if not start_date or not end_date:
        start_date, end_date = _default_date_range()
    rows = query_db(
        """SELECT p.purchase_id, p.invoice_number AS purchase_invoice, p.purchase_date,
               COALESCE(s.supplier_name, 'Unknown') AS supplier_name,
               COALESCE(s.phone, '') AS supplier_phone,
               p.total, p.subtotal, p.discount, p.tax,
               p.payment_status,
               COUNT(pi.purchase_item_id) AS line_items,
               COALESCE(SUM(pi.quantity), 0) AS units_purchased
        FROM purchases p
        LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        LEFT JOIN purchase_items pi ON p.purchase_id = pi.purchase_id
        WHERE p.purchase_date BETWEEN %s AND %s
        GROUP BY p.purchase_id, p.invoice_number, p.purchase_date,
                 s.supplier_name, s.phone, p.total, p.subtotal, p.discount, p.tax,
                 p.payment_status
        ORDER BY p.purchase_date DESC, p.purchase_id DESC""",
        (start_date, end_date)) or []
    purchases = []
    total_cost = Decimal('0.00')
    total_paid = Decimal('0.00')
    total_due = Decimal('0.00')
    total_units = 0
    for r in rows:
        cost = _to_decimal(r['total'])
        units = int(r['units_purchased'] or 0)
        status = r['payment_status'] or 'PAID'
        if status == 'PAID':
            paid = cost
            due = Decimal('0.00')
        elif status == 'PENDING':
            paid = Decimal('0.00')
            due = cost
        else: # PARTIAL or other
            paid = cost / Decimal('2')
            due = cost - paid
        total_cost += cost
        total_paid += paid
        total_due += due
        total_units += units
        purchases.append({'purchase_id': r['purchase_id'],
            'purchase_invoice': r['purchase_invoice'] or '',
            'purchase_date': _fmt_date(r['purchase_date']),
            'supplier_name': r['supplier_name'], 'supplier_phone': r['supplier_phone'],
            'total_amount': float(cost),
            'paid_amount': float(paid),
            'balance_amount': float(due),
            'payment_status': status,
            'payment_method': 'DIRECT',
            'line_items': int(r['line_items'] or 0), 'units_purchased': units})
    sup_rows = query_db(
        """SELECT COALESCE(s.supplier_name, 'Unknown') AS supplier_name,
               COUNT(DISTINCT p.purchase_id) AS bills,
               COALESCE(SUM(p.total), 0) AS total_cost,
               COALESCE(SUM(CASE WHEN p.payment_status = 'PAID' THEN p.total ELSE 0 END), 0) AS total_paid,
               COALESCE(SUM(CASE WHEN p.payment_status != 'PAID' THEN p.total ELSE 0 END), 0) AS total_due
        FROM purchases p LEFT JOIN suppliers s ON p.supplier_id = s.supplier_id
        WHERE p.purchase_date BETWEEN %s AND %s
        GROUP BY s.supplier_name ORDER BY total_cost DESC""",
        (start_date, end_date)) or []
    supplier_breakdown = [{'supplier_name': r['supplier_name'], 'bills': int(r['bills']),
        'total_cost': float(_to_decimal(r['total_cost'])),
        'total_paid': float(_to_decimal(r['total_paid'])),
        'total_due': float(_to_decimal(r['total_due']))} for r in sup_rows]
    return {'start_date': start_date, 'end_date': end_date, 'purchases': purchases,
        'summary': {'bill_count': len(purchases), 'total_cost': float(total_cost),
            'total_paid': float(total_paid), 'total_due': float(total_due),
            'total_units': total_units},
        'supplier_breakdown': supplier_breakdown}


def export_purchase_report_csv(start_date=None, end_date=None):
    data = get_purchase_report(start_date, end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Purchase Invoice', 'Date', 'Supplier', 'Phone', 'Total Cost',
        'Paid', 'Due', 'Status', 'Payment Method', 'Line Items', 'Units Purchased'])
    for p in data['purchases']:
        writer.writerow([p['purchase_invoice'], p['purchase_date'], p['supplier_name'],
            p['supplier_phone'], p['total_amount'], p['paid_amount'],
            p['balance_amount'], p['payment_status'], p['payment_method'],
            p['line_items'], p['units_purchased']])
    writer.writerow([])
    sm = data['summary']
    writer.writerow(['TOTAL', '', '', '', sm['total_cost'], sm['total_paid'],
        sm['total_due'], '', '', sm['bill_count'], sm['total_units']])
    return output.getvalue().encode('utf-8-sig')


def get_inventory_valuation_report():
    rows = query_db(
        """SELECT pv.variant_id, p.product_id, p.product_name,
               COALESCE(c.category_name, 'Uncategorized') AS category_name,
               pv.sku, pv.size, pv.color, pv.stock_quantity, pv.minimum_stock,
               pv.purchase_price, pv.selling_price,
               (pv.stock_quantity * pv.purchase_price) AS stock_value_at_cost,
               (pv.stock_quantity * pv.selling_price) AS stock_value_at_selling
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        LEFT JOIN categories c ON p.category_id = c.category_id
        WHERE pv.status = 'ACTIVE'
        ORDER BY c.category_name, p.product_name, pv.size, pv.color""") or []
    variants = []
    total_units = 0
    total_cost_value = Decimal('0.00')
    total_selling_value = Decimal('0.00')
    low_stock_count = 0
    for r in rows:
        qty = int(r['stock_quantity'] or 0)
        purchase_price = _to_decimal(r['purchase_price'])
        selling_price = _to_decimal(r['selling_price'])
        cost_val = _to_decimal(r['stock_value_at_cost'])
        sell_val = _to_decimal(r['stock_value_at_selling'])
        min_stock = int(r['minimum_stock'] or 0)
        is_low = qty <= min_stock
        total_units += qty
        total_cost_value += cost_val
        total_selling_value += sell_val
        if is_low:
            low_stock_count += 1
        variants.append({'variant_id': r['variant_id'], 'product_id': r['product_id'],
            'product_name': r['product_name'], 'category_name': r['category_name'],
            'sku': r['sku'], 'size': r['size'] or '', 'color': r['color'] or '',
            'stock_quantity': qty, 'minimum_stock': min_stock,
            'purchase_price': float(purchase_price), 'selling_price': float(selling_price),
            'stock_value_at_cost': float(cost_val), 'stock_value_at_selling': float(sell_val),
            'potential_margin': float(sell_val - cost_val), 'is_low_stock': is_low})
    cat_map = {}
    for v in variants:
        cat = v['category_name']
        if cat not in cat_map:
            cat_map[cat] = {'category_name': cat, 'variant_count': 0,
                'total_units': 0, 'cost_value': 0.0, 'selling_value': 0.0}
        cat_map[cat]['variant_count'] += 1
        cat_map[cat]['total_units'] += v['stock_quantity']
        cat_map[cat]['cost_value'] = round(cat_map[cat]['cost_value'] + v['stock_value_at_cost'], 2)
        cat_map[cat]['selling_value'] = round(cat_map[cat]['selling_value'] + v['stock_value_at_selling'], 2)
    category_subtotals = sorted(cat_map.values(), key=lambda x: x['cost_value'], reverse=True)
    return {'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'variants': variants,
        'summary': {'total_variants': len(variants), 'total_units': total_units,
            'total_cost_value': float(total_cost_value),
            'total_selling_value': float(total_selling_value),
            'total_potential_margin': float(total_selling_value - total_cost_value),
            'low_stock_count': low_stock_count},
        'category_subtotals': category_subtotals}


def export_inventory_valuation_csv():
    data = get_inventory_valuation_report()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Category', 'Product', 'SKU', 'Size', 'Color', 'Stock Qty',
        'Min Stock', 'Purchase Price', 'Selling Price', 'Value at Cost',
        'Value at Selling', 'Potential Margin', 'Status'])
    for v in data['variants']:
        writer.writerow([v['category_name'], v['product_name'], v['sku'],
            v['size'], v['color'], v['stock_quantity'], v['minimum_stock'],
            v['purchase_price'], v['selling_price'],
            v['stock_value_at_cost'], v['stock_value_at_selling'],
            v['potential_margin'], 'Low Stock' if v['is_low_stock'] else 'OK'])
    writer.writerow([])
    sm = data['summary']
    writer.writerow(['TOTAL', '', '', '', '', sm['total_units'], '', '', '',
        sm['total_cost_value'], sm['total_selling_value'], sm['total_potential_margin'], ''])
    return output.getvalue().encode('utf-8-sig')


def get_credit_aging_report():
    rows = query_db(
        """SELECT c.customer_id, c.customer_name,
               COALESCE(c.phone, '') AS phone,
               COALESCE(c.address, '') AS address,
               c.credit_limit,
               COALESCE(SUM(CASE
                   WHEN ct.transaction_type = 'CREDIT_SALE' THEN ct.amount
                   WHEN ct.transaction_type IN ('PAYMENT', 'RETURN_REFUND') THEN -ct.amount
                   ELSE 0
               END), 0.00) AS outstanding_balance,
               MIN(CASE WHEN ct.transaction_type = 'CREDIT_SALE' THEN ct.transaction_date END) AS oldest_credit_date
        FROM customers c
        JOIN credit_transactions ct ON c.customer_id = ct.customer_id
        GROUP BY c.customer_id, c.customer_name, c.phone, c.address, c.credit_limit
        HAVING outstanding_balance > 0
        ORDER BY outstanding_balance DESC""") or []
    today = date.today()
    buckets = {'0_30': [], '31_60': [], '61_90': [], '91_plus': []}
    summary_acc = {'0_30': Decimal('0.00'), '31_60': Decimal('0.00'),
        '61_90': Decimal('0.00'), '91_plus': Decimal('0.00'),
        'total': Decimal('0.00'), 'customer_count': 0}
    customers = []
    for r in rows:
        balance = _to_decimal(r['outstanding_balance'])
        if balance <= Decimal('0.00'):
            continue
        oldest_date = r['oldest_credit_date']
        if oldest_date is None:
            age_days = 0
        elif isinstance(oldest_date, (date, datetime)):
            age_date = oldest_date.date() if isinstance(oldest_date, datetime) else oldest_date
            age_days = (today - age_date).days
        else:
            age_days = 0
        if age_days <= 30:
            bucket, bucket_label = '0_30', '0-30 Days'
        elif age_days <= 60:
            bucket, bucket_label = '31_60', '31-60 Days'
        elif age_days <= 90:
            bucket, bucket_label = '61_90', '61-90 Days'
        else:
            bucket, bucket_label = '91_plus', '90+ Days'
        summary_acc[bucket] += balance
        summary_acc['total'] += balance
        summary_acc['customer_count'] += 1
        entry = {'customer_id': r['customer_id'], 'customer_name': r['customer_name'],
            'phone': r['phone'], 'address': r.get('address', ''), 'city': r.get('address', ''),
            'credit_limit': float(_to_decimal(r['credit_limit'])),
            'outstanding_balance': float(balance),
            'oldest_credit_date': _fmt_date(r['oldest_credit_date']),
            'age_days': age_days, 'bucket': bucket, 'bucket_label': bucket_label}
        buckets[bucket].append(entry)
        customers.append(entry)
    for b in buckets:
        buckets[b].sort(key=lambda x: x['outstanding_balance'], reverse=True)
    return {'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'customers': customers, 'buckets': buckets,
        'summary': {'customer_count': summary_acc['customer_count'],
            'total_outstanding': float(summary_acc['total']),
            '0_30_days': float(summary_acc['0_30']),
            '31_60_days': float(summary_acc['31_60']),
            '61_90_days': float(summary_acc['61_90']),
            '91_plus_days': float(summary_acc['91_plus'])}}


def export_credit_aging_csv():
    data = get_credit_aging_report()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Customer', 'Phone', 'Address', 'Credit Limit',
        'Outstanding', 'Oldest Credit Date', 'Age (Days)', 'Bucket'])
    for c in data['customers']:
        writer.writerow([c['customer_name'], c['phone'], c.get('address', c.get('city', '')),
            c['credit_limit'], c['outstanding_balance'],
            c['oldest_credit_date'], c['age_days'], c['bucket_label']])
    writer.writerow([])
    sm = data['summary']
    writer.writerow(['TOTAL', '', '', '', sm['total_outstanding'], '', '', ''])
    writer.writerow(['0-30 Days', '', '', '', sm['0_30_days'], '', '', ''])
    writer.writerow(['31-60 Days', '', '', '', sm['31_60_days'], '', '', ''])
    writer.writerow(['61-90 Days', '', '', '', sm['61_90_days'], '', '', ''])
    writer.writerow(['90+ Days', '', '', '', sm['91_plus_days'], '', '', ''])
    return output.getvalue().encode('utf-8-sig')


def get_profit_report(start_date=None, end_date=None):
    if not start_date or not end_date:
        start_date, end_date = _default_date_range()
    rows = query_db(
        """SELECT p.product_id, p.product_name,
               COALESCE(c.category_name, 'Uncategorized') AS category_name,
               COALESCE(SUM(si.quantity), 0) AS units_sold,
               COALESCE(SUM(si.total_price), 0) AS total_revenue,
               COALESCE(SUM(si.quantity * pv.purchase_price), 0) AS total_cost,
               COALESCE(SUM(si.total_price - (si.quantity * pv.purchase_price)), 0) AS gross_profit
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.sale_id
        JOIN product_variants pv ON si.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        LEFT JOIN categories c ON p.category_id = c.category_id
        WHERE s.sale_date BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name, c.category_name
        ORDER BY gross_profit DESC""",
        (start_date, end_date)) or []
    products = []
    total_revenue = Decimal('0.00')
    total_cost = Decimal('0.00')
    total_profit = Decimal('0.00')
    total_units = 0
    for r in rows:
        rev = _to_decimal(r['total_revenue'])
        cost = _to_decimal(r['total_cost'])
        profit = _to_decimal(r['gross_profit'])
        units = int(r['units_sold'] or 0)
        margin_pct = float((profit / rev * 100).quantize(Decimal('0.01'))) if rev > 0 else 0.0
        total_revenue += rev
        total_cost += cost
        total_profit += profit
        total_units += units
        products.append({'product_id': r['product_id'], 'product_name': r['product_name'],
            'category_name': r['category_name'], 'units_sold': units,
            'total_revenue': float(rev), 'total_cost': float(cost),
            'gross_profit': float(profit), 'margin_percent': margin_pct})
    overall_margin_pct = float(
        (total_profit / total_revenue * 100).quantize(Decimal('0.01'))) if total_revenue > 0 else 0.0
    return {'start_date': start_date, 'end_date': end_date, 'products': products,
        'summary': {'product_count': len(products), 'total_units_sold': total_units,
            'total_revenue': float(total_revenue), 'total_cost': float(total_cost),
            'gross_profit': float(total_profit),
            'overall_margin_percent': overall_margin_pct}}


def export_profit_report_csv(start_date=None, end_date=None):
    data = get_profit_report(start_date, end_date)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Product Name', 'Category', 'Units Sold',
        'Revenue', 'Cost', 'Gross Profit', 'Margin %'])
    for p in data['products']:
        writer.writerow([p['product_name'], p['category_name'], p['units_sold'],
            p['total_revenue'], p['total_cost'], p['gross_profit'], p['margin_percent']])
    writer.writerow([])
    sm = data['summary']
    writer.writerow(['TOTAL', '', sm['total_units_sold'], sm['total_revenue'],
        sm['total_cost'], sm['gross_profit'], sm['overall_margin_percent']])
    return output.getvalue().encode('utf-8-sig')
