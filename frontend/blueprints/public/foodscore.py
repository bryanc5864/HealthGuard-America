"""
Public FoodScore Routes
Food product health scoring for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.foodscore import FoodScoreService


@public_bp.route('/foodscore/')
def foodscore_home():
    """FoodScore module home"""
    stats = FoodScoreService.get_stats()
    high_risk = FoodScoreService.get_high_risk_products(limit=10)
    categories = FoodScoreService.get_categories()
    return render_template('public/foodscore/home.html',
                          stats=stats, high_risk=high_risk, categories=categories)


@public_bp.route('/foodscore/search')
def foodscore_search():
    """Search for food products"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    products = FoodScoreService.get_products(search=query if query else None,
                                             category=category if category else None,
                                             limit=50)
    categories = FoodScoreService.get_categories()
    return render_template('public/foodscore/search.html',
                          query=query, products=products, categories=categories,
                          selected_category=category)


@public_bp.route('/foodscore/scan')
def foodscore_scan():
    """Barcode scanner page"""
    return render_template('public/foodscore/scan.html')


@public_bp.route('/foodscore/product/<barcode>')
def foodscore_product(barcode):
    """View single product details"""
    product = FoodScoreService.get_product(barcode)
    additives = FoodScoreService.get_additives(limit=100)
    return render_template('public/foodscore/product.html',
                          barcode=barcode, product=product, additives=additives)


@public_bp.route('/foodscore/additives')
def foodscore_additives():
    """View all additives"""
    search = request.args.get('q', '')
    additives = FoodScoreService.get_additives(search=search if search else None, limit=100)
    return render_template('public/foodscore/search.html',
                          query=search, additives=additives, show_additives=True)


# API endpoints
@public_bp.route('/api/foodscore/products')
def api_products():
    """API: Get products"""
    search = request.args.get('q', '')
    category = request.args.get('category', '')
    limit = int(request.args.get('limit', 50))
    products = FoodScoreService.get_products(search=search if search else None,
                                             category=category if category else None,
                                             limit=limit)
    return jsonify(products)


@public_bp.route('/api/foodscore/product/<barcode>')
def api_product(barcode):
    """API: Get single product"""
    product = FoodScoreService.get_product(barcode)
    return jsonify(product or {})


@public_bp.route('/api/foodscore/additives')
def api_additives():
    """API: Get additives"""
    search = request.args.get('q', '')
    limit = int(request.args.get('limit', 100))
    additives = FoodScoreService.get_additives(search=search if search else None, limit=limit)
    return jsonify(additives)


@public_bp.route('/api/foodscore/stats')
def api_stats():
    """API: Get statistics"""
    stats = FoodScoreService.get_stats()
    return jsonify(stats)
