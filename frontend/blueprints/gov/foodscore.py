"""
Government FoodScore Routes
Food product health scoring with SNAP analysis
"""
from flask import render_template, request
from . import gov_bp, gov_required


@gov_bp.route('/foodscore/')
@gov_required
def foodscore_home():
    """FoodScore module home"""
    return render_template('gov/foodscore/home.html')


@gov_bp.route('/foodscore/search')
@gov_required
def foodscore_search():
    """Search for food products"""
    query = request.args.get('q', '')
    return render_template('gov/foodscore/search.html', query=query)


@gov_bp.route('/foodscore/product/<barcode>')
@gov_required
def foodscore_product(barcode):
    """View single product details"""
    return render_template('gov/foodscore/product.html', barcode=barcode)


@gov_bp.route('/foodscore/snap')
@gov_required
def foodscore_snap():
    """SNAP eligibility health analysis (gov-only)"""
    return render_template('gov/foodscore/snap.html')
