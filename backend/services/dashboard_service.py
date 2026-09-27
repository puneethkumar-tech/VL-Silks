"""
VL Silks - Dashboard Service
Authoritative business logic for shop overview, live statistics,
sales analytics charts, top garment items, and low-stock alerts.
"""
from decimal import Decimal
from datetime import datetime, date
from backend.utils.database import query_db
from backend.services import credit_service


def get_dashboard_summary():
    """
    Compute comprehensive dashboard summary statistics across products,
    stock, sales, returns, and credit ledgers.
    """
    # 1. Product & Category counts
    catalog_stats = query_db("""
        SELECT 
            (SELECT COUNT(*) FROM products WHERE status = 'ACTIVE') AS total_products,
            (SELECT COUNT(*) FROM categories WHERE status = 'ACTIVE') AS total_categories,
            (SELECT COUNT(*) FROM product_variants WHERE status = 'ACTIVE') AS total_variants,
            (SELECT COALESCE(SUM(stock_quantity), 0) FROM product_variants WHERE status = 'ACTIVE') AS total_stock,
            (SELECT COUNT(*) FROM product_variants WHERE status = 'ACTIVE' AND stock_quantity <= minimum_stock) AS low_stock_count
    """, one=True) or {}

    # 2. Sales Summary (Today, This Month, and All-Time)
    sales_stats = query_db("""
        SELECT 
            COALESCE(SUM(CASE WHEN sale_date = CURDATE() THEN total_amount ELSE 0 END), 0) AS today_sales,
            COALESCE(SUM(CASE WHEN sale_date = CURDATE() THEN 1 ELSE 0 END), 0) AS today_sales_count,
            COALESCE(SUM(CASE WHEN sale_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01') THEN total_amount ELSE 0 END), 0) AS month_sales,
            COALESCE(SUM(CASE WHEN sale_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01') THEN 1 ELSE 0 END), 0) AS month_sales_count,
            COALESCE(SUM(total_amount), 0) AS total_sales_all_time,
            COALESCE(COUNT(*), 0) AS total_sales_count_all_time
        FROM sales
    """, one=True) or {}

    # 3. Returns Summary (Today & This Month)
    returns_stats = query_db("""
        SELECT 
            COALESCE(SUM(CASE WHEN return_date = CURDATE() THEN total_refund_amount ELSE 0 END), 0) AS today_returns_amount,
            COALESCE(SUM(CASE WHEN return_date = CURDATE() THEN 1 ELSE 0 END), 0) AS today_returns_count,
            COALESCE(SUM(CASE WHEN return_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01') THEN total_refund_amount ELSE 0 END), 0) AS month_returns_amount,
            COALESCE(SUM(CASE WHEN return_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01') THEN 1 ELSE 0 END), 0) AS month_returns_count
        FROM returns
    """, one=True) or {}

    # 4. Credit / Udhaar Summary
    credit_summary = credit_service.get_credit_summary()

    today_sales = Decimal(str(sales_stats.get('today_sales', 0)))
    today_returns = Decimal(str(returns_stats.get('today_returns_amount', 0)))
    today_net_sales = today_sales - today_returns

    month_sales = Decimal(str(sales_stats.get('month_sales', 0)))
    month_returns = Decimal(str(returns_stats.get('month_returns_amount', 0)))
    month_net_sales = month_sales - month_returns

    return {
        "total_products": int(catalog_stats.get('total_products', 0)),
        "total_categories": int(catalog_stats.get('total_categories', 0)),
        "total_variants": int(catalog_stats.get('total_variants', 0)),
        "total_stock": int(catalog_stats.get('total_stock', 0)),
        "low_stock_count": int(catalog_stats.get('low_stock_count', 0)),
        "today_sales": float(today_sales),
        "today_sales_count": int(sales_stats.get('today_sales_count', 0)),
        "today_returns_amount": float(today_returns),
        "today_returns_count": int(returns_stats.get('today_returns_count', 0)),
        "today_net_sales": float(today_net_sales),
        "month_sales": float(month_sales),
        "month_sales_count": int(sales_stats.get('month_sales_count', 0)),
        "month_returns_amount": float(month_returns),
        "month_returns_count": int(returns_stats.get('month_returns_count', 0)),
        "month_net_sales": float(month_net_sales),
        "total_sales_all_time": float(Decimal(str(sales_stats.get('total_sales_all_time', 0)))),
        "total_sales_count_all_time": int(sales_stats.get('total_sales_count_all_time', 0)),
        "total_credit_to_collect": float(credit_summary.get('total_credit_to_collect', 0)),
        "customers_with_credit": int(credit_summary.get('total_credit_customers', 0)),
        "total_credit_limit": float(credit_summary.get('total_credit_limit', 0))
    }


def get_recent_sales(limit=6):
    """
    Retrieve latest completed sales transactions for dashboard display.
    """
    rows = query_db("""
        SELECT 
            s.sale_id, 
            s.invoice_number, 
            s.sale_date, 
            s.total_amount, 
            s.paid_amount, 
            s.balance_amount, 
            s.payment_status, 
            s.payment_method,
            c.customer_name,
            c.phone AS customer_phone
        FROM sales s
        LEFT JOIN customers c ON s.customer_id = c.customer_id
        ORDER BY s.sale_date DESC, s.sale_id DESC
        LIMIT %s
    """, (limit,)) or []

    results = []
    for r in rows:
        results.append({
            "sale_id": r['sale_id'],
            "invoice_number": r['invoice_number'],
            "sale_date": r['sale_date'].strftime('%Y-%m-%d') if isinstance(r['sale_date'], (date, datetime)) else str(r['sale_date'] or ''),
            "total_amount": float(Decimal(str(r['total_amount']))),
            "paid_amount": float(Decimal(str(r['paid_amount']))),
            "balance_amount": float(Decimal(str(r['balance_amount']))),
            "payment_status": r['payment_status'],
            "payment_method": r['payment_method'],
            "customer_name": r['customer_name'] or 'Walk-in Customer',
            "customer_phone": r.get('customer_phone') or ''
        })
    return results


def get_low_stock_items(limit=15):
    """
    Retrieve product variants where stock is below or equal to threshold.
    """
    rows = query_db("""
        SELECT 
            pv.variant_id, 
            pv.product_id,
            p.product_name, 
            c.category_name,
            pv.sku, 
            pv.size, 
            pv.color, 
            pv.stock_quantity, 
            pv.minimum_stock,
            pv.selling_price
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.product_id
        LEFT JOIN categories c ON p.category_id = c.category_id
        WHERE pv.status = 'ACTIVE' AND pv.stock_quantity <= pv.minimum_stock
        ORDER BY pv.stock_quantity ASC, pv.variant_id ASC
        LIMIT %s
    """, (limit,)) or []

    results = []
    for r in rows:
        results.append({
            "variant_id": r['variant_id'],
            "product_id": r['product_id'],
            "product_name": r['product_name'],
            "category_name": r['category_name'] or '',
            "sku": r['sku'],
            "size": r['size'],
            "color": r['color'],
            "stock_quantity": int(r['stock_quantity']),
            "minimum_stock": int(r['minimum_stock']),
            "selling_price": float(Decimal(str(r['selling_price'])))
        })
    return results


def get_monthly_sales(months=6):
    """
    Aggregate sales by month for the past N months.
    Returns month labels, total sales revenue, invoice counts, and net amounts.
    """
    rows = query_db("""
        SELECT 
            DATE_FORMAT(sale_date, '%Y-%m') AS month_key,
            DATE_FORMAT(sale_date, '%b %Y') AS month_label,
            COALESCE(SUM(total_amount), 0) AS total_sales,
            COALESCE(SUM(paid_amount), 0) AS total_paid,
            COALESCE(SUM(balance_amount), 0) AS total_credit,
            COUNT(*) AS invoice_count
        FROM sales
        WHERE sale_date >= DATE_SUB(DATE_FORMAT(CURDATE(), '%Y-%m-01'), INTERVAL %s MONTH)
        GROUP BY DATE_FORMAT(sale_date, '%Y-%m'), DATE_FORMAT(sale_date, '%b %Y')
        ORDER BY month_key ASC
    """, (max(months - 1, 0),)) or []

    monthly_map = {r['month_key']: r for r in rows}

    # Generate chronological sequence for the last N months up to current month
    labels = []
    sales_data = []
    paid_data = []
    credit_data = []
    counts_data = []
    monthly_details = []

    current_date = date.today()
    cur_year = current_date.year
    cur_month = current_date.month

    for i in range(months - 1, -1, -1):
        m = cur_month - i
        y = cur_year
        while m <= 0:
            m += 12
            y -= 1
        month_key = f"{y:04d}-{m:02d}"
        month_label = date(y, m, 1).strftime('%b %Y')

        labels.append(month_label)
        rec = monthly_map.get(month_key)
        if rec:
            t_sales = float(Decimal(str(rec['total_sales'])))
            t_paid = float(Decimal(str(rec['total_paid'])))
            t_credit = float(Decimal(str(rec['total_credit'])))
            cnt = int(rec['invoice_count'])
        else:
            t_sales = 0.0
            t_paid = 0.0
            t_credit = 0.0
            cnt = 0

        sales_data.append(t_sales)
        paid_data.append(t_paid)
        credit_data.append(t_credit)
        counts_data.append(cnt)
        monthly_details.append({
            "month_key": month_key,
            "month_label": month_label,
            "total_sales": t_sales,
            "total_paid": t_paid,
            "total_credit": t_credit,
            "invoice_count": cnt
        })

    return {
        "labels": labels,
        "sales": sales_data,
        "paid": paid_data,
        "credit": credit_data,
        "counts": counts_data,
        "details": monthly_details
    }


def get_top_products(limit=5):
    """
    Retrieve top selling garment products ranked by units sold and revenue.
    """
    rows = query_db("""
        SELECT 
            p.product_id,
            p.product_name,
            c.category_name,
            COALESCE(SUM(si.quantity), 0) AS total_units_sold,
            COALESCE(SUM(si.total_price), 0) AS total_revenue,
            COUNT(DISTINCT s.sale_id) AS orders_count
        FROM sale_items si
        JOIN sales s ON si.sale_id = s.sale_id
        JOIN product_variants pv ON si.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        LEFT JOIN categories c ON p.category_id = c.category_id
        GROUP BY p.product_id, p.product_name, c.category_name
        ORDER BY total_units_sold DESC, total_revenue DESC
        LIMIT %s
    """, (limit,)) or []

    results = []
    for r in rows:
        results.append({
            "product_id": r['product_id'],
            "product_name": r['product_name'],
            "category_name": r['category_name'] or 'Uncategorized',
            "total_units_sold": int(r['total_units_sold']),
            "total_revenue": float(Decimal(str(r['total_revenue']))),
            "orders_count": int(r['orders_count'])
        })
    return results


def get_category_distribution():
    """
    Category-wise sales distribution breakdown for analytics donut/pie chart.
    """
    rows = query_db("""
        SELECT 
            COALESCE(c.category_name, 'Uncategorized') AS category_name,
            COALESCE(SUM(si.total_price), 0) AS category_revenue,
            COALESCE(SUM(si.quantity), 0) AS units_sold
        FROM sale_items si
        JOIN product_variants pv ON si.variant_id = pv.variant_id
        JOIN products p ON pv.product_id = p.product_id
        LEFT JOIN categories c ON p.category_id = c.category_id
        GROUP BY c.category_name
        ORDER BY category_revenue DESC
    """) or []

    categories = []
    revenue = []
    units = []
    details = []

    for r in rows:
        rev = float(Decimal(str(r['category_revenue'])))
        u = int(r['units_sold'])
        categories.append(r['category_name'])
        revenue.append(rev)
        units.append(u)
        details.append({
            "category_name": r['category_name'],
            "revenue": rev,
            "units_sold": u
        })

    return {
        "categories": categories,
        "revenue": revenue,
        "units": units,
        "details": details
    }
