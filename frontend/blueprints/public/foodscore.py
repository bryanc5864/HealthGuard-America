"""
Public FoodScore Routes
Food product health scoring for consumers
"""
from flask import render_template, request
from . import public_bp


@public_bp.route('/foodscore/')
def foodscore_home():
    """FoodScore module home"""
    return render_template('public/foodscore/home.html')


@public_bp.route('/foodscore/search')
def foodscore_search():
    """Search for food products"""
    query = request.args.get('q', '')
    return render_template('public/foodscore/search.html', query=query)


@public_bp.route('/foodscore/scan')
def foodscore_scan():
    """Barcode scanner page"""
    return render_template('public/foodscore/scan.html')


@public_bp.route('/foodscore/product/<barcode>')
def foodscore_product(barcode):
    """View single product details"""
    return render_template('public/foodscore/product.html', barcode=barcode)
