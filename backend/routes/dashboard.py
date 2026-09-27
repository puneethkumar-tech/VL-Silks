"""
VL Silks - Dashboard Routes & API Endpoints
Main overview blueprint for shop metrics, monthly sales charts,
top-performing garments, and real-time dashboard data.
"""
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, request
from backend.routes.auth import login_required
from backend.services import dashboard_service, credit_service

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def home():
    """Home route redirects to dashboard if authenticated, else login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main shop dashboard view."""
    summary = dashboard_service.get_dashboard_summary()
    recent_sales = dashboard_service.get_recent_sales(limit=6)
    low_stock_items = dashboard_service.get_low_stock_items(limit=8)
    top_products = dashboard_service.get_top_products(limit=5)
    credit_customers = credit_service.get_credit_customers(status='ACTIVE')
    monthly_sales = dashboard_service.get_monthly_sales(months=6)
    category_dist = dashboard_service.get_category_distribution()

    return render_template(
        'dashboard.html',
        summary=summary,
        recent_sales=recent_sales,
        credit_customers=credit_customers,
        low_stock_items=low_stock_items,
        top_products=top_products,
        monthly_sales=monthly_sales,
        category_dist=category_dist
    )


@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def api_dashboard_summary():
    """JSON API for real-time dashboard metrics."""
    try:
        summary = dashboard_service.get_dashboard_summary()
        return jsonify({
            "status": "success",
            "data": summary
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/recent-sales', methods=['GET'])
def api_dashboard_recent_sales():
    """JSON API for latest sales transactions."""
    try:
        limit = request.args.get('limit', default=6, type=int)
        sales = dashboard_service.get_recent_sales(limit=limit)
        return jsonify({
            "status": "success",
            "count": len(sales),
            "data": sales
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/low-stock', methods=['GET'])
def api_dashboard_low_stock():
    """JSON API for product variants below minimum threshold."""
    try:
        limit = request.args.get('limit', default=15, type=int)
        items = dashboard_service.get_low_stock_items(limit=limit)
        return jsonify({
            "status": "success",
            "count": len(items),
            "data": items
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/monthly-sales', methods=['GET'])
def api_dashboard_monthly_sales():
    """JSON API for monthly sales chart data."""
    try:
        months = request.args.get('months', default=6, type=int)
        data = dashboard_service.get_monthly_sales(months=months)
        return jsonify({
            "status": "success",
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/top-products', methods=['GET'])
def api_dashboard_top_products():
    """JSON API for top-selling garment products."""
    try:
        limit = request.args.get('limit', default=5, type=int)
        products = dashboard_service.get_top_products(limit=limit)
        return jsonify({
            "status": "success",
            "count": len(products),
            "data": products
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@dashboard_bp.route('/api/dashboard/category-distribution', methods=['GET'])
def api_dashboard_category_distribution():
    """JSON API for sales category distribution chart."""
    try:
        data = dashboard_service.get_category_distribution()
        return jsonify({
            "status": "success",
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
