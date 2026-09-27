from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request, Response
from backend.routes.auth import login_required
from backend.services import report_service

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def index():
    return render_template('reports/index.html')


# ---------- SALES REPORT ----------

@reports_bp.route('/reports/sales')
@login_required
def sales():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    data = report_service.get_sales_report(start_date or None, end_date or None)
    return render_template('reports/sales.html', report=data,
        start_date=data['start_date'], end_date=data['end_date'])


@reports_bp.route('/api/reports/sales')
def api_sales():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        data = report_service.get_sales_report(start_date, end_date)
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@reports_bp.route('/api/reports/sales/csv')
def export_sales_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        csv_bytes = report_service.export_sales_report_csv(start_date, end_date)
        filename = f'vl_silks_sales_{start_date or "all"}_{end_date or "all"}.csv'
        return Response(csv_bytes, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------- PURCHASE REPORT ----------

@reports_bp.route('/reports/purchases')
@login_required
def purchases():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    data = report_service.get_purchase_report(start_date or None, end_date or None)
    return render_template('reports/purchases.html', report=data,
        start_date=data['start_date'], end_date=data['end_date'])


@reports_bp.route('/api/reports/purchases')
def api_purchases():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        data = report_service.get_purchase_report(start_date, end_date)
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@reports_bp.route('/api/reports/purchases/csv')
def export_purchases_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        csv_bytes = report_service.export_purchase_report_csv(start_date, end_date)
        filename = f'vl_silks_purchases_{start_date or "all"}_{end_date or "all"}.csv'
        return Response(csv_bytes, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------- INVENTORY VALUATION ----------

@reports_bp.route('/reports/inventory-valuation')
@login_required
def inventory_valuation():
    data = report_service.get_inventory_valuation_report()
    return render_template('reports/inventory_valuation.html', report=data)


@reports_bp.route('/api/reports/inventory-valuation')
def api_inventory_valuation():
    try:
        data = report_service.get_inventory_valuation_report()
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@reports_bp.route('/api/reports/inventory-valuation/csv')
def export_inventory_valuation_csv():
    try:
        csv_bytes = report_service.export_inventory_valuation_csv()
        return Response(csv_bytes, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=vl_silks_inventory_valuation.csv'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------- CREDIT AGING ----------

@reports_bp.route('/reports/credit-aging')
@login_required
def credit_aging():
    data = report_service.get_credit_aging_report()
    return render_template('reports/credit_aging.html', report=data)


@reports_bp.route('/api/reports/credit-aging')
def api_credit_aging():
    try:
        data = report_service.get_credit_aging_report()
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@reports_bp.route('/api/reports/credit-aging/csv')
def export_credit_aging_csv():
    try:
        csv_bytes = report_service.export_credit_aging_csv()
        return Response(csv_bytes, mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=vl_silks_credit_aging.csv'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ---------- PROFIT REPORT ----------

@reports_bp.route('/reports/profit')
@login_required
def profit():
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    data = report_service.get_profit_report(start_date or None, end_date or None)
    return render_template('reports/profit.html', report=data,
        start_date=data['start_date'], end_date=data['end_date'])


@reports_bp.route('/api/reports/profit')
def api_profit():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        data = report_service.get_profit_report(start_date, end_date)
        return jsonify({'status': 'success', 'data': data}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@reports_bp.route('/api/reports/profit/csv')
def export_profit_csv():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        csv_bytes = report_service.export_profit_report_csv(start_date, end_date)
        filename = f'vl_silks_profit_{start_date or "all"}_{end_date or "all"}.csv'
        return Response(csv_bytes, mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
