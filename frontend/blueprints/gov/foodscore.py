"""
Government FoodScore Routes
Food product health scoring with SNAP analysis
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from services.foodscore import FoodScoreService


@gov_bp.route('/foodscore/')
@gov_required
def foodscore_home():
    """FoodScore module home"""
    stats = FoodScoreService.get_stats()
    high_risk = FoodScoreService.get_high_risk_products(limit=10)
    categories = FoodScoreService.get_categories()
    return render_template('gov/foodscore/home.html',
                          stats=stats, high_risk=high_risk, categories=categories)


@gov_bp.route('/foodscore/search')
@gov_required
def foodscore_search():
    """Search for food products"""
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    products = FoodScoreService.get_products(search=query if query else None,
                                             category=category if category else None,
                                             limit=50)
    categories = FoodScoreService.get_categories()
    return render_template('gov/foodscore/search.html',
                          query=query, products=products, categories=categories,
                          selected_category=category)


@gov_bp.route('/foodscore/product/<barcode>')
@gov_required
def foodscore_product(barcode):
    """View single product details"""
    product = FoodScoreService.get_product(barcode)
    additives = FoodScoreService.get_additives(limit=100)
    return render_template('gov/foodscore/product.html',
                          barcode=barcode, product=product, additives=additives)


@gov_bp.route('/foodscore/snap')
@gov_required
def foodscore_snap():
    """SNAP eligibility health analysis (gov-only)"""
    stats = FoodScoreService.get_stats()
    nova_dist = FoodScoreService.get_nova_distribution()
    products = FoodScoreService.get_products(limit=100)

    # Analyze SNAP-eligible products (simplified - based on categories)
    snap_analysis = {
        'total_products': len(products),
        'nova_distribution': nova_dist,
        'avg_health_score': 0,
        'high_risk_count': 0
    }

    health_scores = []
    for p in products:
        score = p.get('maha_score', p.get('health_score', 50))
        if score:
            health_scores.append(float(score))
        if float(score or 50) < 40:
            snap_analysis['high_risk_count'] += 1

    if health_scores:
        snap_analysis['avg_health_score'] = round(sum(health_scores) / len(health_scores), 1)

    high_risk = FoodScoreService.get_high_risk_products(limit=20)

    return render_template('gov/foodscore/snap.html',
                          stats=stats, snap_analysis=snap_analysis,
                          high_risk=high_risk, nova_dist=nova_dist)


@gov_bp.route('/foodscore/additives')
@gov_required
def foodscore_additives():
    """Additive alerts and risk analysis (gov-only)"""
    search = request.args.get('q', '')
    additives = FoodScoreService.get_additives(search=search if search else None, limit=200)
    stats = FoodScoreService.get_stats()

    # Categorize additives by risk level
    high_risk_additives = [a for a in additives if float(a.get('risk_score', a.get('score', 50))) >= 70]
    medium_risk = [a for a in additives if 40 <= float(a.get('risk_score', a.get('score', 50))) < 70]
    low_risk = [a for a in additives if float(a.get('risk_score', a.get('score', 50))) < 40]

    return render_template('gov/foodscore/additives.html',
                          additives=additives, stats=stats, search=search,
                          high_risk=high_risk_additives, medium_risk=medium_risk, low_risk=low_risk)
