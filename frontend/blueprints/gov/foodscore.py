"""
Government FoodScore Routes
Food product health scoring with SNAP analysis
"""
from flask import render_template, request, jsonify
from . import gov_bp, gov_required
import sys
import logging
from pathlib import Path

# Add project root to path for ML imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
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


def enrich_products_with_ml_risk(products):
    """Add ML additive risk scores to a list of products for search results."""
    if not products:
        return products

    additive_service = get_additive_service()
    if not additive_service:
        return products

    for product in products:
        try:
            additive_tags = product.get('additives_tags', '')
            if additive_tags:
                additive_names = [a.replace('en:', '').strip() for a in additive_tags.split(',') if a.strip()]
                if additive_names:
                    results = additive_service.score_batch(additive_names)
                    if results:
                        scores = [r.risk_score for r in results]
                        product['ml_additive_risk_score'] = round(max(scores), 1)
        except Exception as e:
            logger.error(f"Failed to score additives for product: {e}")

    return products


def batch_classify_nova(products):
    """Batch classify products with NOVA service for SNAP analysis."""
    nova_service = get_nova_service()
    if not nova_service or not products:
        return None

    # Collect products with ingredients
    products_with_ingredients = []
    ingredient_texts = []
    for p in products:
        ingredients = p.get('ingredients_text', '')
        if ingredients:
            products_with_ingredients.append(p)
            ingredient_texts.append(ingredients)

    if not ingredient_texts:
        return None

    try:
        results = nova_service.classify_batch(ingredient_texts)

        # Build ML NOVA distribution
        ml_nova_dist = {1: 0, 2: 0, 3: 0, 4: 0}
        disagreements = []

        for i, (product, result) in enumerate(zip(products_with_ingredients, results)):
            ml_nova_dist[result.nova_group] += 1

            # Check for disagreement
            stored_nova = str(product.get('nova_group', ''))
            stored_num = None
            for char in stored_nova:
                if char.isdigit():
                    stored_num = int(char)
                    break
            if stored_num and stored_num != result.nova_group:
                disagreements.append({
                    'product_name': product.get('product_name', 'Unknown'),
                    'stored_nova': stored_num,
                    'ml_nova': result.nova_group,
                    'confidence': round(result.confidence * 100, 1)
                })

        return {
            'ml_nova_distribution': ml_nova_dist,
            'classified_count': len(results),
            'disagreements': disagreements[:10],  # Top 10 disagreements
            'disagreement_count': len(disagreements)
        }
    except Exception as e:
        logger.error(f"Batch NOVA classification failed: {e}")
        return None


def analyze_additive_patterns(products):
    """Analyze risky additive patterns across products for SNAP analysis."""
    additive_service = get_additive_service()
    if not additive_service or not products:
        return None

    try:
        additive_frequency = {}  # additive_name -> {count, total_risk, products}

        for product in products:
            additive_tags = product.get('additives_tags', '')
            if additive_tags:
                additive_names = [a.replace('en:', '').strip() for a in additive_tags.split(',') if a.strip()]
                for name in additive_names:
                    if name not in additive_frequency:
                        result = additive_service.score_additive(name)
                        additive_frequency[name] = {
                            'count': 0,
                            'risk_score': result.risk_score,
                            'risk_category': result.risk_category,
                            'products': []
                        }
                    additive_frequency[name]['count'] += 1
                    if len(additive_frequency[name]['products']) < 3:
                        additive_frequency[name]['products'].append(product.get('product_name', 'Unknown')[:30])

        # Find most common high-risk additives
        high_risk_patterns = [
            {
                'name': name,
                'count': data['count'],
                'risk_score': round(data['risk_score'], 1),
                'example_products': data['products']
            }
            for name, data in additive_frequency.items()
            if data['risk_category'] == 'high'
        ]
        high_risk_patterns.sort(key=lambda x: x['count'], reverse=True)

        return {
            'total_unique_additives': len(additive_frequency),
            'high_risk_additive_count': len(high_risk_patterns),
            'most_common_high_risk': high_risk_patterns[:10]
        }
    except Exception as e:
        logger.error(f"Additive pattern analysis failed: {e}")
        return None


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
    # Enrich with ML additive risk scores
    products = enrich_products_with_ml_risk(products)

    categories = FoodScoreService.get_categories()
    return render_template('gov/foodscore/search.html',
                          query=query, products=products, categories=categories,
                          selected_category=category)


@gov_bp.route('/foodscore/product/<barcode>')
@gov_required
def foodscore_product(barcode):
    """View single product details"""
    product = FoodScoreService.get_product(barcode)
    # Enrich with ML inference results
    product = enrich_product_with_ml(product)

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

    # ML Analysis: Batch NOVA classification
    ml_nova_analysis = batch_classify_nova(products)

    # ML Analysis: Additive risk patterns
    ml_additive_patterns = analyze_additive_patterns(products)

    return render_template('gov/foodscore/snap.html',
                          stats=stats, snap_analysis=snap_analysis,
                          high_risk=high_risk, nova_dist=nova_dist,
                          ml_nova_analysis=ml_nova_analysis,
                          ml_additive_patterns=ml_additive_patterns)


@gov_bp.route('/foodscore/analyze')
@gov_required
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

        # Helper to safely parse nutrition values
        def safe_float(val, default=0):
            if not val:
                return default
            try:
                return float(val.replace('g', '').replace('mg', '').strip())
            except (ValueError, AttributeError):
                return default

        # Analyze nutrition
        if sugars and safe_float(sugars) > 10:
            health_concerns.append({'issue': 'High Sugar', 'value': sugars, 'note': 'More than 10g per serving'})
        if sodium and safe_float(sodium) > 500:
            health_concerns.append({'issue': 'High Sodium', 'value': sodium, 'note': 'More than 500mg per serving'})
        if saturated_fat and safe_float(saturated_fat) > 5:
            health_concerns.append({'issue': 'High Saturated Fat', 'value': saturated_fat, 'note': 'More than 5g per serving'})

        if fiber and safe_float(fiber) >= 3:
            health_positives.append({'benefit': 'Good Fiber Source', 'value': fiber})
        if protein and safe_float(protein) >= 5:
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

    return render_template('gov/foodscore/analyze.html',
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


@gov_bp.route('/api/foodscore/ocr', methods=['POST'])
@gov_required
def api_foodscore_ocr():
    """API: OCR nutrition label from uploaded image."""
    import re
    import io

    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image file provided'})

    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No image file selected'})

    # Check file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'success': False, 'error': 'Invalid image format'})

    try:
        # Read image data
        image_data = file.read()

        # Try to use pytesseract for OCR
        ocr_text = None
        try:
            from PIL import Image
            import pytesseract

            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')

            ocr_text = pytesseract.image_to_string(image)
            logger.info(f"OCR extracted {len(ocr_text)} characters")
        except ImportError:
            logger.warning("pytesseract not available")
        except Exception as e:
            logger.error(f"OCR failed: {e}")

        if not ocr_text:
            return jsonify({
                'success': False,
                'error': 'OCR processing unavailable. Please enter nutrition information manually.'
            })

        # Parse the OCR text
        result = parse_nutrition_label(ocr_text)
        result['success'] = True
        result['raw_text'] = ocr_text[:500]

        return jsonify(result)

    except Exception as e:
        logger.error(f"Image processing error: {e}")
        return jsonify({'success': False, 'error': str(e)})


def parse_nutrition_label(text):
    """Parse OCR text to extract nutrition facts."""
    import re

    result = {}
    text = text.replace('\n', ' ').replace('\r', ' ')
    text_lower = text.lower()

    # Extract serving size
    serving_match = re.search(r'serving\s*size[:\s]*([^\d]*\d+[^\n,]*)', text_lower)
    if serving_match:
        result['serving_size'] = serving_match.group(1).strip()[:50]

    # Extract calories
    cal_match = re.search(r'calories[:\s]*(\d+)', text_lower)
    if cal_match:
        result['calories'] = cal_match.group(1)

    # Extract total fat
    fat_match = re.search(r'total\s*fat[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if fat_match:
        result['total_fat'] = fat_match.group(1)

    # Extract saturated fat
    sat_fat_match = re.search(r'saturated\s*fat[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if sat_fat_match:
        result['saturated_fat'] = sat_fat_match.group(1)

    # Extract sodium
    sodium_match = re.search(r'sodium[:\s]*(\d+)\s*m?g', text_lower)
    if sodium_match:
        result['sodium'] = sodium_match.group(1)

    # Extract total carbohydrates
    carb_match = re.search(r'total\s*carb(?:ohydrate)?s?[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if carb_match:
        result['total_carbs'] = carb_match.group(1)

    # Extract sugars
    sugar_match = re.search(r'(?:total\s*)?sugars?[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if sugar_match:
        result['sugars'] = sugar_match.group(1)

    # Extract protein
    protein_match = re.search(r'protein[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if protein_match:
        result['protein'] = protein_match.group(1)

    # Extract fiber
    fiber_match = re.search(r'(?:dietary\s*)?fiber[:\s]*(\d+\.?\d*)\s*g', text_lower)
    if fiber_match:
        result['fiber'] = fiber_match.group(1)

    # Extract ingredients
    ing_match = re.search(r'ingredients[:\s]*([^\.]+\.)', text_lower)
    if ing_match:
        result['ingredients'] = ing_match.group(1).strip()[:500]

    return result
