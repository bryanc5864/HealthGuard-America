"""
Public FoodScore Routes
Food product health scoring for consumers
"""
from flask import render_template, request, jsonify
from . import public_bp
import sys
import logging
from pathlib import Path

# Add frontend directory to path for service imports
FRONTEND_DIR = Path(__file__).parent.parent.parent
PROJECT_ROOT = FRONTEND_DIR.parent
sys.path.insert(0, str(FRONTEND_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from services.foodscore import FoodScoreService

# ML Services - lazy loaded
_nova_service = None
_additive_service = None
logger = logging.getLogger(__name__)


def get_nova_service():
    """Lazy load NOVA classification service."""
    global _nova_service
    if _nova_service is None:
        try:
            from ml.nova_classifier.inference import NovaClassificationService
            _nova_service = NovaClassificationService.load()
            logger.info("NOVA classification service loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NOVA service: {e}")
            _nova_service = False  # Mark as failed to avoid repeated attempts
    return _nova_service if _nova_service else None


def get_additive_service():
    """Lazy load Additive risk service."""
    global _additive_service
    if _additive_service is None:
        try:
            from ml.additive_scorer.inference import AdditiveRiskService
            _additive_service = AdditiveRiskService.load()
            logger.info("Additive risk service loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Additive service: {e}")
            _additive_service = False  # Mark as failed to avoid repeated attempts
    return _additive_service if _additive_service else None


def enrich_product_with_ml(product):
    """Add ML inference results to a product dict."""
    if not product:
        return product

    # NOVA classification
    nova_service = get_nova_service()
    if nova_service:
        try:
            ingredients = product.get('ingredients_text', '')
            if ingredients:
                nova_result = nova_service.classify(ingredients)
                product['ml_nova_group'] = nova_result.nova_group
                product['ml_nova_confidence'] = round(nova_result.confidence * 100, 1)
                product['ml_nova_description'] = nova_result.description
                product['ml_nova_probabilities'] = nova_result.probabilities
                product['ml_nova_is_confident'] = nova_result.is_confident

                # Check for disagreement with stored value
                stored_nova = str(product.get('nova_group', ''))
                if stored_nova:
                    # Extract numeric value from stored nova
                    stored_num = None
                    for char in stored_nova:
                        if char.isdigit():
                            stored_num = int(char)
                            break
                    if stored_num and stored_num != nova_result.nova_group:
                        product['ml_nova_disagreement'] = True
                        product['ml_nova_stored'] = stored_num
        except Exception as e:
            logger.error(f"NOVA classification failed for product: {e}")

    # Additive scoring
    additive_service = get_additive_service()
    if additive_service:
        try:
            ingredients = product.get('ingredients_text', '')
            additive_tags = product.get('additives_tags', '')

            # Try to score additives from tags first
            if additive_tags:
                additive_names = [a.replace('en:', '').strip() for a in additive_tags.split(',') if a.strip()]
                if additive_names:
                    additive_results = additive_service.score_batch(additive_names)
                    product['ml_additive_risks'] = [
                        {
                            'name': r.name,
                            'risk_score': round(r.risk_score, 1),
                            'risk_category': r.risk_category,
                            'fda_status': r.fda_status,
                            'eu_status': r.eu_status,
                            'is_artificial': r.is_artificial
                        }
                        for r in additive_results
                    ]
                    # Calculate aggregate score
                    if additive_results:
                        scores = [r.risk_score for r in additive_results]
                        product['ml_additive_max_risk'] = round(max(scores), 1)
                        product['ml_additive_avg_risk'] = round(sum(scores) / len(scores), 1)
                        product['ml_additive_high_risk_count'] = sum(1 for r in additive_results if r.risk_category == 'high')

            # Also analyze from ingredients text if available
            elif ingredients:
                analysis = additive_service.score_product_ingredients(ingredients)
                product['ml_additive_risks'] = [
                    {
                        'name': r.name,
                        'risk_score': round(r.risk_score, 1),
                        'risk_category': r.risk_category,
                        'fda_status': r.fda_status,
                        'eu_status': r.eu_status,
                        'is_artificial': r.is_artificial
                    }
                    for r in analysis['additives']
                ]
                product['ml_additive_max_risk'] = round(analysis['max_risk_score'], 1)
                product['ml_additive_avg_risk'] = round(analysis['avg_risk_score'], 1)
                product['ml_additive_high_risk_count'] = len(analysis['high_risk_additives'])
        except Exception as e:
            logger.error(f"Additive scoring failed for product: {e}")

    return product


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
    # Enrich with ML inference results
    product = enrich_product_with_ml(product)

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
    """API: Get single product with ML inference"""
    product = FoodScoreService.get_product(barcode)
    # Enrich with ML inference results
    product = enrich_product_with_ml(product)
    return jsonify(product or {})


@public_bp.route('/api/foodscore/additives')
def api_additives():
    """API: Get additives"""
    search = request.args.get('q', '')
    limit = int(request.args.get('limit', 100))
    additives = FoodScoreService.get_additives(search=search if search else None, limit=limit)
    return jsonify(additives)


@public_bp.route('/foodscore/analyze')
def foodscore_analyze():
    """Analyze nutrition label data - user enters ingredients and nutrition facts."""
    # Get submitted data
    ingredients = request.args.get('ingredients', '')
    product_name = request.args.get('product_name', '')
    serving_size = request.args.get('serving_size', '')
    calories = request.args.get('calories', '')
    total_fat = request.args.get('total_fat', '')
    saturated_fat = request.args.get('saturated_fat', '')
    sodium = request.args.get('sodium', '')
    total_carbs = request.args.get('total_carbs', '')
    sugars = request.args.get('sugars', '')
    protein = request.args.get('protein', '')
    fiber = request.args.get('fiber', '')
    submitted = request.args.get('submitted', '')

    analysis = None
    ml_results = {}

    if submitted and ingredients:
        # Build a mock product for ML analysis
        mock_product = {
            'product_name': product_name or 'User-Entered Product',
            'ingredients_text': ingredients,
            'serving_size': serving_size,
        }

        # Parse nutrition values
        try:
            if calories:
                mock_product['energy_kcal_100g'] = float(calories.replace('g', '').strip())
            if total_fat:
                mock_product['fat_100g'] = float(total_fat.replace('g', '').strip())
            if saturated_fat:
                mock_product['saturated_fat_100g'] = float(saturated_fat.replace('g', '').strip())
            if sodium:
                mock_product['sodium_100g'] = float(sodium.replace('mg', '').strip())
            if total_carbs:
                mock_product['carbohydrates_100g'] = float(total_carbs.replace('g', '').strip())
            if sugars:
                mock_product['sugars_100g'] = float(sugars.replace('g', '').strip())
            if protein:
                mock_product['proteins_100g'] = float(protein.replace('g', '').strip())
            if fiber:
                mock_product['fiber_100g'] = float(fiber.replace('g', '').strip())
        except ValueError:
            pass

        # Run ML analysis
        ml_results = enrich_product_with_ml(mock_product)

        # Calculate simple health scores
        health_concerns = []
        health_positives = []

        # Analyze nutrition
        if sugars and float(sugars.replace('g', '').strip()) > 10:
            health_concerns.append({'issue': 'High Sugar', 'value': sugars, 'note': 'More than 10g per serving'})
        if sodium and float(sodium.replace('mg', '').strip()) > 500:
            health_concerns.append({'issue': 'High Sodium', 'value': sodium, 'note': 'More than 500mg per serving'})
        if saturated_fat and float(saturated_fat.replace('g', '').strip()) > 5:
            health_concerns.append({'issue': 'High Saturated Fat', 'value': saturated_fat, 'note': 'More than 5g per serving'})

        if fiber and float(fiber.replace('g', '').strip()) >= 3:
            health_positives.append({'benefit': 'Good Fiber Source', 'value': fiber})
        if protein and float(protein.replace('g', '').strip()) >= 5:
            health_positives.append({'benefit': 'Good Protein Source', 'value': protein})

        # Calculate a simple health score (0-100)
        base_score = 70
        if ml_results.get('ml_nova_group'):
            nova_penalty = {1: 0, 2: 5, 3: 15, 4: 30}.get(ml_results['ml_nova_group'], 15)
            base_score -= nova_penalty
        base_score -= len(health_concerns) * 10
        base_score += len(health_positives) * 5
        base_score = max(10, min(100, base_score))

        analysis = {
            'product_name': product_name or 'User-Entered Product',
            'health_score': base_score,
            'health_concerns': health_concerns,
            'health_positives': health_positives,
            'ml_results': ml_results,
        }

    return render_template('public/foodscore/analyze.html',
                          ingredients=ingredients,
                          product_name=product_name,
                          serving_size=serving_size,
                          calories=calories,
                          total_fat=total_fat,
                          saturated_fat=saturated_fat,
                          sodium=sodium,
                          total_carbs=total_carbs,
                          sugars=sugars,
                          protein=protein,
                          fiber=fiber,
                          analysis=analysis,
                          submitted=bool(submitted))


@public_bp.route('/api/foodscore/stats')
def api_stats():
    """API: Get statistics"""
    stats = FoodScoreService.get_stats()
    return jsonify(stats)
