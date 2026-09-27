import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from backend.routes.auth import login_required, admin_required
from backend.services import product_service
from backend.services.product_service import ValidationError

products_bp = Blueprint('products', __name__)

# =========================================================================
# WEB ROUTES
# =========================================================================

@products_bp.route('/products')
@login_required
def index():
    """List all garments and their variants with filters."""
    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', '').strip()
    status = request.args.get('status', 'ALL').strip()

    category_id_int = int(category_id) if category_id and category_id.isdigit() else None

    products_list = product_service.get_all_products(
        search=search if search else None,
        category_id=category_id_int,
        status=status if status != 'ALL' else None
    )
    categories = product_service.get_all_categories()

    # Calculate summary metrics
    total_products_count = len(products_list)
    total_stock_count = sum(p['total_stock'] for p in products_list)
    total_variants_count = sum(p['variant_count'] for p in products_list)

    return render_template(
        'products/index.html',
        products=products_list,
        categories=categories,
        current_search=search,
        current_category=category_id_int,
        current_status=status,
        total_products_count=total_products_count,
        total_stock_count=total_stock_count,
        total_variants_count=total_variants_count
    )

@products_bp.route('/products/new', methods=['GET', 'POST'])
@admin_required
def new():
    """Create a new product with multiple variants."""
    categories = product_service.get_all_categories()

    if request.method == 'POST':
        product_data = {
            'product_name': request.form.get('product_name', '').strip(),
            'category_id': request.form.get('category_id', ''),
            'brand': request.form.get('brand', 'VL Silks').strip() or 'VL Silks',
            'material': request.form.get('material', '').strip(),
            'description': request.form.get('description', '').strip(),
            'status': request.form.get('status', 'ACTIVE')
        }

        # Parse dynamic variants from form
        # Form fields use indexing: variant_sku[], variant_size[], variant_color[], etc.
        skus = request.form.getlist('variant_sku[]')
        sizes = request.form.getlist('variant_size[]')
        colors = request.form.getlist('variant_color[]')
        purchase_prices = request.form.getlist('variant_purchase_price[]')
        selling_prices = request.form.getlist('variant_selling_price[]')
        stocks = request.form.getlist('variant_stock[]')
        min_stocks = request.form.getlist('variant_min_stock[]')
        barcodes = request.form.getlist('variant_barcode[]')

        variants_data = []
        for i in range(len(skus)):
            if skus[i].strip():
                variants_data.append({
                    'sku': skus[i].strip(),
                    'size': sizes[i].strip() if i < len(sizes) else 'Free Size',
                    'color': colors[i].strip() if i < len(colors) else 'Standard',
                    'purchase_price': purchase_prices[i] if i < len(purchase_prices) and purchase_prices[i] else 0,
                    'selling_price': selling_prices[i] if i < len(selling_prices) and selling_prices[i] else 0,
                    'stock_quantity': stocks[i] if i < len(stocks) and stocks[i] else 0,
                    'minimum_stock': min_stocks[i] if i < len(min_stocks) and min_stocks[i] else 5,
                    'barcode': barcodes[i].strip() if i < len(barcodes) and barcodes[i].strip() else None,
                    'status': 'ACTIVE'
                })

        try:
            user_id = session.get('user_id')
            product_id = product_service.create_product_with_variants(
                product_data, variants_data, user_id=user_id
            )
            flash(f"Garment '{product_data['product_name']}' created successfully with {len(variants_data)} variant(s)!", "success")
            return redirect(url_for('products.view', product_id=product_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
            return render_template(
                'products/new.html',
                categories=categories,
                form_data=product_data,
                variants_data=variants_data
            )
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template(
                'products/new.html',
                categories=categories,
                form_data=product_data,
                variants_data=variants_data
            )

    return render_template('products/new.html', categories=categories, form_data={}, variants_data=[])

@products_bp.route('/products/<int:product_id>')
@login_required
def view(product_id):
    """View product details and all variants with stock status badges."""
    product = product_service.get_product_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    variants = product_service.get_product_variants(product_id)
    total_stock = sum(v['stock_quantity'] for v in variants)
    in_stock_count = sum(1 for v in variants if v['stock_status'] == 'IN_STOCK')
    low_stock_count = sum(1 for v in variants if v['stock_status'] == 'LOW_STOCK')
    out_stock_count = sum(1 for v in variants if v['stock_status'] == 'OUT_OF_STOCK')

    return render_template(
        'products/view.html',
        product=product,
        variants=variants,
        total_stock=total_stock,
        in_stock_count=in_stock_count,
        low_stock_count=low_stock_count,
        out_stock_count=out_stock_count
    )

@products_bp.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit(product_id):
    """Edit base product and manage its variants."""
    product = product_service.get_product_by_id(product_id)
    if not product:
        flash("Product not found.", "danger")
        return redirect(url_for('products.index'))

    categories = product_service.get_all_categories()
    variants = product_service.get_product_variants(product_id)

    if request.method == 'POST':
        product_data = {
            'product_name': request.form.get('product_name', '').strip(),
            'category_id': request.form.get('category_id', ''),
            'brand': request.form.get('brand', 'VL Silks').strip() or 'VL Silks',
            'material': request.form.get('material', '').strip(),
            'description': request.form.get('description', '').strip(),
            'status': request.form.get('status', 'ACTIVE')
        }

        try:
            product_service.update_product(product_id, product_data)
            flash(f"Product '{product_data['product_name']}' updated successfully!", "success")
            return redirect(url_for('products.view', product_id=product_id))
        except ValidationError as e:
            flash(f"Validation Error: {str(e)}", "danger")
        except Exception as e:
            flash(f"Error updating product: {str(e)}", "danger")

    return render_template(
        'products/edit.html',
        product=product,
        categories=categories,
        variants=variants
    )

@products_bp.route('/products/<int:product_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_status(product_id):
    """Toggle active/inactive status of a base product."""
    try:
        new_status = product_service.toggle_product_status(product_id)
        flash(f"Product status updated to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update product status: {str(e)}", "danger")
    return redirect(request.referrer or url_for('products.index'))

@products_bp.route('/products/<int:product_id>/variants/add', methods=['POST'])
@admin_required
def add_variant(product_id):
    """Add a new variant to an existing product."""
    variant_data = {
        'sku': (request.form.get('sku') or '').strip(),
        'size': (request.form.get('size') or '').strip(),
        'color': (request.form.get('color') or '').strip(),
        'purchase_price': (request.form.get('purchase_price') or '').strip(),
        'selling_price': (request.form.get('selling_price') or '').strip(),
        'stock_quantity': (request.form.get('stock_quantity') or '').strip(),
        'minimum_stock': (request.form.get('minimum_stock') or '').strip(),
        'barcode': (request.form.get('barcode') or '').strip() or None,
        'status': (request.form.get('status') or 'ACTIVE').strip()
    }

    try:
        user_id = session.get('user_id')
        variant_id = product_service.add_variant_to_product(product_id, variant_data, user_id=user_id)
        flash(f"Variant '{variant_data['sku']}' added successfully!", "success")
    except ValidationError as e:
        flash(f"Variant Validation Error: {str(e)}", "danger")
    except Exception as e:
        flash(f"Error adding variant: {str(e)}", "danger")

    return redirect(url_for('products.edit', product_id=product_id))

@products_bp.route('/products/variants/<int:variant_id>/edit', methods=['POST'])
@admin_required
def edit_variant(variant_id):
    """Update variant properties (prices, min stock, barcode, status). Stock is NOT modified directly."""
    variant = product_service.get_variant_by_id(variant_id)
    if not variant:
        flash("Variant not found.", "danger")
        return redirect(url_for('products.index'))

    variant_data = {
        'sku': (request.form.get('sku') or '').strip(),
        'size': (request.form.get('size') or '').strip(),
        'color': (request.form.get('color') or '').strip(),
        'purchase_price': (request.form.get('purchase_price') or '').strip(),
        'selling_price': (request.form.get('selling_price') or '').strip(),
        'minimum_stock': (request.form.get('minimum_stock') or '').strip(),
        'barcode': (request.form.get('barcode') or '').strip() or None,
        'status': (request.form.get('status') or 'ACTIVE').strip()
    }

    try:
        product_service.update_variant(variant_id, variant_data)
        flash(f"Variant '{variant_data['sku']}' updated successfully!", "success")
    except ValidationError as e:
        flash(f"Variant Validation Error: {str(e)}", "danger")
    except Exception as e:
        flash(f"Error updating variant: {str(e)}", "danger")

    return redirect(url_for('products.edit', product_id=variant['product_id']))

@products_bp.route('/products/variants/<int:variant_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_variant_status(variant_id):
    """Toggle active/inactive status of a product variant."""
    variant = product_service.get_variant_by_id(variant_id)
    if not variant:
        flash("Variant not found.", "danger")
        return redirect(url_for('products.index'))

    try:
        new_status = product_service.toggle_variant_status(variant_id)
        flash(f"Variant '{variant['sku']}' status changed to {new_status}.", "info")
    except ValidationError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Failed to update variant status: {str(e)}", "danger")

    return redirect(request.referrer or url_for('products.view', product_id=variant['product_id']))


# =========================================================================
# REST API ENDPOINTS (API_SPEC.md)
# =========================================================================

@products_bp.route('/api/products', methods=['GET'])
def api_get_products():
    """GET /api/products - List products with optional search, category, status."""
    search = request.args.get('search')
    category_id = request.args.get('category_id')
    status = request.args.get('status')

    category_id_int = int(category_id) if category_id and category_id.isdigit() else None
    products_list = product_service.get_all_products(
        search=search, category_id=category_id_int, status=status
    )
    return jsonify({"status": "success", "count": len(products_list), "data": products_list}), 200

@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
def api_get_product(product_id):
    """GET /api/products/:id - Single product with variants."""
    product = product_service.get_product_by_id(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Product not found"}), 404

    variants = product_service.get_product_variants(product_id)
    product['variants'] = variants
    return jsonify({"status": "success", "data": product}), 200

@products_bp.route('/api/products', methods=['POST'])
def api_create_product():
    """POST /api/products - Create product with variants (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    data = request.get_json() or {}
    product_data = data.get('product', {})
    variants_data = data.get('variants', [])

    try:
        product_id = product_service.create_product_with_variants(
            product_data, variants_data, user_id=session.get('user_id')
        )
        return jsonify({
            "status": "success",
            "message": "Product created successfully",
            "product_id": product_id
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    """PUT /api/products/:id - Update base product (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    product = product_service.get_product_by_id(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Product not found"}), 404

    data = request.get_json() or {}
    try:
        product_service.update_product(product_id, data)
        return jsonify({"status": "success", "message": "Product updated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """DELETE /api/products/:id - Safe deactivation of product (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        product_service.toggle_product_status(product_id, new_status='INACTIVE')
        return jsonify({"status": "success", "message": "Product deactivated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/api/products/<int:product_id>/variants', methods=['GET'])
def api_get_variants(product_id):
    """GET /api/products/:id/variants - Fetch variants for a product."""
    product = product_service.get_product_by_id(product_id)
    if not product:
        return jsonify({"status": "error", "message": "Product not found"}), 404

    variants = product_service.get_product_variants(product_id)
    return jsonify({"status": "success", "count": len(variants), "data": variants}), 200

@products_bp.route('/api/products/<int:product_id>/variants', methods=['POST'])
def api_create_variant(product_id):
    """POST /api/products/:id/variants - Add a variant to a product (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    variant_data = request.get_json() or {}
    try:
        variant_id = product_service.add_variant_to_product(
            product_id, variant_data, user_id=session.get('user_id')
        )
        return jsonify({
            "status": "success",
            "message": "Variant created successfully",
            "variant_id": variant_id
        }), 201
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/api/products/variants/<int:variant_id>', methods=['PUT'])
def api_update_variant(variant_id):
    """PUT /api/products/variants/:variant_id - Update a variant (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    variant = product_service.get_variant_by_id(variant_id)
    if not variant:
        return jsonify({"status": "error", "message": "Variant not found"}), 404

    data = request.get_json() or {}
    try:
        product_service.update_variant(variant_id, data)
        return jsonify({"status": "success", "message": "Variant updated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@products_bp.route('/api/products/variants/<int:variant_id>', methods=['DELETE'])
def api_delete_variant(variant_id):
    """DELETE /api/products/variants/:variant_id - Deactivate a variant (Admin)."""
    if 'user_id' not in session or session.get('user_role') != 'ADMIN':
        return jsonify({"status": "error", "message": "Admin authorization required"}), 403

    try:
        product_service.toggle_variant_status(variant_id, new_status='INACTIVE')
        return jsonify({"status": "success", "message": "Variant deactivated successfully"}), 200
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
